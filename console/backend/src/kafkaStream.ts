// This project was developed with assistance from AI tools.
import { Kafka, type Consumer, type EachMessagePayload } from "kafkajs";
import { EventEmitter } from "node:events";

export interface SimpleLogger {
  info(obj: unknown, msg?: string): void;
  warn(obj: unknown, msg?: string): void;
  error(obj: unknown, msg?: string): void;
}

export interface FleetMessage {
  receivedAt: string;
  topic: string;
  partition: number;
  offset: string;
  key: string | null;
  payload: unknown;
}

export class FleetStream extends EventEmitter {
  private readonly kafka: Kafka;
  private consumer: Consumer | undefined;
  private diagMsgCount = 0;
  private diagLastReportTs = Date.now();
  private readonly DIAG_INTERVAL_MS = 30_000;

  constructor(
    bootstrapServers: string,
    private readonly topics: string[],
    private readonly groupId: string,
    private readonly clientId: string,
    private readonly log: SimpleLogger,
  ) {
    super();
    this.kafka = new Kafka({
      clientId: this.clientId,
      brokers: bootstrapServers.split(","),
    });
  }

  async start(): Promise<void> {
    this.consumer = this.kafka.consumer({
      groupId: `${this.groupId}-${Date.now()}`,
      sessionTimeout: 45_000,
      heartbeatInterval: 5_000,
      allowAutoTopicCreation: false,
      // Lower than the kafkajs default (5s) so the UI feels responsive.
      // At 200ms each poll returns quickly; with nothing pending, the
      // consumer is in a tight loop but it's trivial work on a backend
      // that's already idle most of the time.
      maxWaitTimeInMs: 200,
    });

    this.consumer.on(this.consumer.events.CRASH, (event) => {
      this.log.error({ err: event.payload.error?.message, groupId: event.payload.groupId }, "fleet-stream.crash");
    });
    this.consumer.on(this.consumer.events.DISCONNECT, () => {
      this.log.warn({}, "fleet-stream.disconnect");
    });
    this.consumer.on(this.consumer.events.GROUP_JOIN, (event) => {
      this.log.info({ groupId: event.payload.groupId }, "fleet-stream.group-join");
    });

    await this.consumer.connect();
    for (const topic of this.topics) {
      // fromBeginning:false — only tail new messages. Historical messages in
      // these topics may be zstd-compressed from earlier producer versions;
      // kafkajs 2.x doesn't decode zstd natively. New messages use gzip.
      await this.consumer.subscribe({ topic, fromBeginning: false });
    }
    this.log.info({ topics: this.topics }, "fleet-stream subscribed");

    await this.consumer.run({
      autoCommit: true,
      eachMessage: async (payload: EachMessagePayload) => {
        try {
          const msg = this.decode(payload);
          this.diagMsgCount++;
          const now = Date.now();
          if (now - this.diagLastReportTs >= this.DIAG_INTERVAL_MS) {
            const elapsed = (now - this.diagLastReportTs) / 1000;
            this.log.info(
              {
                totalMessages: this.diagMsgCount,
                rate: (this.diagMsgCount / elapsed).toFixed(1),
                sseListeners: this.listenerCount("message"),
              },
              "fleet-stream.diag",
            );
            this.diagLastReportTs = now;
          }
          this.emit("message", msg);
        } catch (err) {
          this.log.error({ err: (err as Error).message, topic: payload.topic }, "fleet-stream.each-error");
        }
      },
    });
  }

  private decode(payload: EachMessagePayload): FleetMessage {
    let parsed: unknown = null;
    const raw = payload.message.value?.toString("utf-8") ?? "";
    if (raw) {
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }
    }
    return {
      receivedAt: new Date().toISOString(),
      topic: payload.topic,
      partition: payload.partition,
      offset: payload.message.offset,
      key: payload.message.key?.toString("utf-8") ?? null,
      payload: parsed,
    };
  }

  async stop(): Promise<void> {
    if (this.consumer) {
      try {
        await this.consumer.disconnect();
      } catch (err) {
        this.log.warn({ err }, "fleet-stream disconnect failed");
      }
    }
  }
}
