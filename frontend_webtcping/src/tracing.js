import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { Resource } from "@opentelemetry/resources";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { XMLHttpRequestInstrumentation } from "@opentelemetry/instrumentation-xml-http-request";

// Traces go to the same origin (nginx /otlp/ -> OpenTelemetry Collector), so no CORS is needed.
// Same-origin /api/* calls get a W3C traceparent header, which joins the browser span to the backend span.
// The k8s.* attributes let Kubemap match these spans to the frontend Deployment (browser spans get none from the Collector).
// A tracing failure must never stop the app from starting.
try {
  const provider = new WebTracerProvider({
    resource: new Resource({
      "service.name": "tcping-frontend",
      "service.namespace": "tcping",
      "k8s.namespace.name": "tcping",
      "k8s.deployment.name": "frontend"
    })
  });
  provider.addSpanProcessor(
    new BatchSpanProcessor(new OTLPTraceExporter({ url: window.location.origin + "/otlp/v1/traces" }))
  );
  provider.register();

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({ ignoreUrls: [/\/otlp\//] }),
      new XMLHttpRequestInstrumentation({ ignoreUrls: [/\/otlp\//] })
    ]
  });
} catch (e) {
  console.warn("OpenTelemetry tracing disabled:", e);
}
