// This project was developed with assistance from AI tools.
export interface AppConfig {
  port: number;
  logLevel: string;
  kafkaBootstrapServers: string;
  kafkaClientId: string;
  kafkaConsumerGroup: string;
  kafkaTopics: string[];
  wmsStubBaseUrl: string;
  kasManagerBaseUrl: string;
  kasIngressDomain: string;
  kasDefaultAppId: string;
  kasDefaultAppVersion: string;
  kasDefaultProfile: string;
  turnUrl: string;
  turnUsername: string;
  turnCredential: string;
}

export function loadConfig(): AppConfig {
  return {
    port: parseInt(process.env.PORT ?? "8090", 10),
    logLevel: process.env.LOG_LEVEL ?? "info",
    kafkaBootstrapServers:
      process.env.KAFKA_BOOTSTRAP_SERVERS ??
      "fleet-kafka-bootstrap.fleet-ops.svc.cluster.local:9092",
    kafkaClientId: process.env.KAFKA_CLIENT_ID ?? "showcase-console",
    kafkaConsumerGroup:
      process.env.KAFKA_CONSUMER_GROUP ?? "showcase-console",
    kafkaTopics:
      (process.env.KAFKA_TOPICS ?? "fleet.events,fleet.missions,fleet.ops.events,fleet.telemetry,fleet.safety.alerts").split(","),
    wmsStubBaseUrl:
      process.env.WMS_STUB_BASE_URL ?? "http://wms-stub.fleet-ops.svc.cluster.local:8082",
    kasManagerBaseUrl:
      process.env.KAS_MANAGER_BASE_URL ?? "http://streaming.omni-streaming.svc.cluster.local:80",
    kasIngressDomain:
      process.env.KAS_INGRESS_DOMAIN ?? "",
    kasDefaultAppId: process.env.KAS_DEFAULT_APP_ID ?? "isaac-sim",
    kasDefaultAppVersion: process.env.KAS_DEFAULT_APP_VERSION ?? "5.1.0",
    kasDefaultProfile: process.env.KAS_DEFAULT_PROFILE ?? "warehouse",
    turnUrl: process.env.TURN_URL ?? "",
    turnUsername: process.env.TURN_USERNAME ?? "",
    turnCredential: process.env.TURN_CREDENTIAL ?? "",
  };
}
