"""Manual spans for streaming (SSE) work. No-ops when OpenTelemetry is not installed."""
from contextlib import contextmanager

try:
    from opentelemetry import context as _context, trace as _trace
    _tracer = _trace.get_tracer("tcping.probes")
except ImportError:
    _context = _trace = _tracer = None


def capture():
    """Current context; call while the request span is still active."""
    return _context.get_current() if _context else None


@contextmanager
def span(name, ctx, **attrs):
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name, context=ctx, attributes=attrs) as s:
        yield s


def run_probe(ctx, name, fn, probe_ip, *args):
    """Run fn(*args) in its own child span (worker thread safe)."""
    with span(name, ctx, **{"probe.ip": probe_ip}):
        return fn(*args)


@contextmanager
def batch(name, ctx, **attrs):
    """Span that covers a whole stream. Not made current, so it is safe inside a generator;
    yields the context that probe spans must use as their parent."""
    if _tracer is None:
        yield ctx
        return
    s = _tracer.start_span(name, context=ctx, attributes=attrs)
    try:
        yield _trace.set_span_in_context(s, ctx)
    except GeneratorExit:
        s.set_attribute("client.disconnected", True)
        raise
    except Exception as e:
        s.record_exception(e)
        s.set_status(_trace.Status(_trace.StatusCode.ERROR, str(e)))
        raise
    finally:
        s.end()
