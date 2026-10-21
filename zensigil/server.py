"""Loopback-only playground. Deliberately not a production hosting server."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from . import run, check, test, failure, __version__
from .errors import SigilError
from .jsonio import loads
from .contracts import MAX_CONTRACT_BYTES, diagnostic
from .proposals import proposal_diagnostic

PACKAGE = Path(__file__).resolve().parent
WEB = PACKAGE / "web"
EXAMPLES = PACKAGE.parent / "examples"
if not EXAMPLES.is_dir():
    EXAMPLES = PACKAGE / "demo"
CATALOG = [
    ("hello", "Hello, ZenSigil", "No input needed"),
    ("namespace-lab", "Namespaced libraries", "Public APIs, private helpers and independent modules"),
    ("sequence-lab", "Running totals & summaries", "Cumulative folds, extrema and record construction"),
    ("closure-lab", "Closures & function factories", "Reusable transformations with captured values"),
    ("typed-data", "Nested types & optional values", "Runtime checks for collections and alternatives"),
    ("collection-lab", "Grouping & collection analysis", "Grouping, counting, partitioning and flattening"),
    ("algorithms", "Algorithms & typed state", "An iterative greatest common divisor"),
    ("transformations", "Collection transformations", "Pure callbacks and structured output"),
    ("module-lab", "Modules & executable tests", "Reusable source, bundled locally"),
    ("decimal-lab", "Exact decimal text", "Explicit arithmetic and rounding"),
    ("reading-list", "Reading list", "Choose your next book"),
    ("event-capacity", "Event capacity", "Review event spaces"),
    ("project-budget", "Project budget", "Review project spending"),
    ("stock-review", "Stock review", "5 products · configurable policy"),
    ("restock", "Restock review", "5 inventory items"),
    ("shipments", "Shipment discrepancies", "3 shipments"),
    ("margins", "Margin review", "4 products"),
    ("functions", "Pure functions", "No input needed"),
    ("records", "Records & lists", "No input needed"),
    ("optional", "Optional fields", "2 people"),
    ("support", "Support triage", "2 support tickets"),
    ("duplicates", "Duplicate proposals", "3 input records"),
    ("error", "A helpful error", "Intentionally missing a field"),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "ZenSigil/0.6"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=True, allow_nan=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "Use the local playground address."})
        route = unquote(urlsplit(self.path).path)
        if route == "/api/language":
            from .syntax import WORDS
            from .checker import BUILTINS
            from .typesys import TYPE_NAMES
            return self.send(200, {"version": __version__, "keywords": sorted(WORDS), "builtins": BUILTINS, "types": sorted(TYPE_NAMES)})
        if route == "/api/health":
            return self.send(200, {"status": "ok", "version": __version__})
        if route == "/api/examples":
            examples = [{"id": key, "title": title, "summary": summary,
                         "source": (EXAMPLES / f"{key}.zs").read_text(encoding="utf-8"),
                         "data": loads((EXAMPLES / f"{key}.json").read_text(encoding="utf-8")),
                         "contract": (loads((EXAMPLES / f"{key}.contract.json").read_text(encoding="utf-8"))
                                      if (EXAMPLES / f"{key}.contract.json").is_file() else None),
                         "modules": (loads((EXAMPLES / f"{key}.modules.json").read_text(encoding="utf-8"))
                                      if (EXAMPLES / f"{key}.modules.json").is_file() else {}),
                         "proposal_contract": (loads((EXAMPLES / f"{key}.proposal.json").read_text(encoding="utf-8"))
                                      if (EXAMPLES / f"{key}.proposal.json").is_file() else None)}
                        for key, title, summary in CATALOG]
            return self.send(200, examples)
        if route == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        if "\x00" in route:
            return self.send(400, {"error": "Invalid path."})
        target = (WEB / ("index.html" if route == "/" else route.lstrip("/"))).resolve()
        if not target.is_relative_to(WEB.resolve()) or not target.is_file():
            return self.send(404, {"error": "Not found. Build the playground first if this is a fresh source checkout."})
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        return self.send(200, target.read_bytes(), content_type)

    def do_POST(self):
        port = self.server.server_port
        origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        origin = self.headers.get("Origin")
        if not self.valid_host() or (origin is not None and origin not in origins):
            return self.send(403, {"error": "Only requests from the local playground are accepted."})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send(415, {"error": "Send application/json."})
        route = urlsplit(self.path).path
        if route not in {"/api/run", "/api/check", "/api/test", "/api/format"}:
            return self.send(404, {"error": "Not found."})
        def reply(result):
            if not result.get("ok", False):
                result.setdefault("values", [])
            if route == "/api/test":
                result.update(mode="test")
                for key in ("total", "passed", "failed"):
                    result.setdefault(key, 0)
                result.setdefault("tests", [])
                result.setdefault("stats", {"steps": 0, "passed": 0, "failed": 0})
            return self.send(200, result)

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_097_152:
                return self.send(413, {"error": "Request must contain at most 2 MiB of JSON."})
            body = loads(self.rfile.read(length).decode("utf-8"))
            if type(body) is not dict or not isinstance(body.get("source"), str):
                raise ValueError("Provide source text and input data.")
            if route == "/api/format":
                from .formatter import format_source
                try:
                    return reply({"ok": True, "version": __version__, "source": format_source(body["source"])})
                except SigilError as error:
                    return reply(failure(error, body["source"]))
            if route == "/api/test" and "data" not in body and "data_text" not in body:
                body["data"] = None
            if "data_text" in body:
                if "data" in body or not isinstance(body["data_text"], str):
                    raise ValueError("Provide either data or data_text, not both.")
                if len(body["data_text"].encode("utf-8")) > 1_048_576:
                    raise ValueError("Input data exceeds 1 MiB.")
                body["data"] = loads(body["data_text"])
            if type(body.get("data")) is not dict and not (route == "/api/test" and body.get("data") is None):
                raise ValueError("Input data must be a JSON object.")
        except (ValueError, RecursionError, TimeoutError) as error:
            return self.send(400, {"error": f"Invalid request: {error}"})
        contract = None
        try:
            if "contract" in body and "contract_text" in body:
                raise ValueError("Provide either contract or contract_text, not both.")
            if "contract_text" in body:
                if type(body["contract_text"]) is not str:
                    raise ValueError("contract_text must contain JSON text.")
                if len(body["contract_text"].encode("utf-8")) > MAX_CONTRACT_BYTES:
                    raise ValueError("Contract exceeds 256 KiB.")
                contract = loads(body["contract_text"])
            elif "contract" in body:
                contract = body["contract"]
            if ("contract" in body or "contract_text" in body) and type(contract) is not dict:
                raise ValueError("Contract must be a JSON object.")
        except (ValueError, RecursionError) as error:
            return reply({"ok": False, "version": __version__, "mode": "preview", "proposals": [], "notes": [],
                                   "diagnostics": [diagnostic("E_CONTRACT", "$", str(error))]})
        proposal_contract = None
        try:
            if "proposal_contract" in body and "proposal_contract_text" in body:
                raise ValueError("Provide either proposal_contract or proposal_contract_text, not both.")
            if "proposal_contract_text" in body:
                if type(body["proposal_contract_text"]) is not str:
                    raise ValueError("proposal_contract_text must contain JSON text.")
                if len(body["proposal_contract_text"].encode("utf-8")) > MAX_CONTRACT_BYTES:
                    raise ValueError("Proposal contract exceeds 256 KiB.")
                proposal_contract = loads(body["proposal_contract_text"])
            elif "proposal_contract" in body:
                proposal_contract = body["proposal_contract"]
            if ("proposal_contract" in body or "proposal_contract_text" in body) and type(proposal_contract) is not dict:
                raise ValueError("Proposal contract must be a JSON object mapping actions to contracts.")
        except (ValueError, RecursionError) as error:
            return reply({"ok": False, "version": __version__, "mode": "preview", "proposals": [], "notes": [],
                                   "diagnostics": [proposal_diagnostic("E_PROPOSAL_CONTRACT", "$", str(error))]})
        if "modules" in body and type(body["modules"]) is not dict:
            return reply(failure(SigilError("E_IMPORT", "modules must be an object of source files."), body["source"]))
        operation = {"/api/run": run, "/api/check": check, "/api/test": test}[route]
        result = operation(body["source"], body["data"], contract=contract,
                           proposal_contract=proposal_contract, modules=body.get("modules"))
        reply(result)


def serve(port=8765):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    if not (WEB / "index.html").is_file():
        raise ValueError("Playground build missing. Run npm ci and npm run build inside playground/.")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"ZenSigil playground: http://127.0.0.1:{port}\nLocal preview only. Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
