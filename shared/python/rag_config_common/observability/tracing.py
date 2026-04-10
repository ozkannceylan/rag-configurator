"""OpenTelemetry setup helpers shared by Python services."""

from __future__ import annotations

from typing import Optional

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    OTEL_AVAILABLE = False


def setup_tracing(
    app,
    *,
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    endpoint: Optional[str] = None,
) -> None:
    """Configure OpenTelemetry tracing for a FastAPI service."""
    if not OTEL_AVAILABLE:
        return

    if getattr(app.state, "_rag_configurator_tracing", False):
        return

    existing_provider = trace.get_tracer_provider()
    if getattr(existing_provider, "_rag_configurator_tracing", False):
        FastAPIInstrumentor.instrument_app(app)
        app.state._rag_configurator_tracing = True
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )
    provider = TracerProvider(resource=resource)

    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    provider._rag_configurator_tracing = True  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    app.state._rag_configurator_tracing = True
