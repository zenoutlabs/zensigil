"""Public ZenSigil API with optional input and proposal contracts."""
from .contracts import contract_diagnostics, input_diagnostics, diagnostic
from .proposals import proposal_contract_diagnostics, proposal_diagnostics
from .checker import Checker
from .errors import SigilError
from .runtime import Runtime, validate_value, validate_step_limit, compact, MAX_JSON_BYTES
from .modules import compile_program
from .testing import TestResultBudget, bound_test_result, run_test_program

__version__ = "0.8.0"


class ContractFailure(Exception):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics


def prepare(source, data=None, contract=None, proposal_contract=None, modules=None):
    if proposal_contract is not None:
        diagnostics = proposal_contract_diagnostics(proposal_contract)
        if diagnostics:
            raise ContractFailure(diagnostics)
    if contract is not None:
        diagnostics = contract_diagnostics(contract)
        if diagnostics:
            raise ContractFailure(diagnostics)
    if data is not None:
        if type(data) is not dict:
            if contract is not None:
                raise ContractFailure([diagnostic("E_INPUT_DATA", "$", "Input data must be a JSON object with named root fields.")])
            raise SigilError("E_INPUT", "Input data must be a JSON object with named root fields.")
        try:
            validate_value(data)
            if len(compact(data).encode("utf-8")) > MAX_JSON_BYTES:
                raise SigilError("E_INPUT", "Input data exceeds 1 MiB.")
        except SigilError as error:
            if contract is not None:
                raise ContractFailure([diagnostic("E_INPUT_DATA", "$", error.message)]) from error
            raise
    if contract is not None and data is not None:
        diagnostics = input_diagnostics(data, contract)
        if diagnostics:
            raise ContractFailure(diagnostics)
    program, _ = compile_program(source, modules)
    possible_inputs = Checker(program, None if data is None else data.keys()).check(program)
    return program, possible_inputs


def located(diagnostic, source, modules=None):
    name = diagnostic.get("source_name", diagnostic.get("source_file", "<program>"))
    actual = source if name in ("", "<program>") else (modules.get(name, "") if type(modules) is dict else "")
    lines = actual.split("\n") if type(actual) is str else []
    line = diagnostic.get("line", 0)
    diagnostic["source_line"] = lines[line - 1] if 0 < line <= len(lines) else ""
    for frame in diagnostic.get("call_trace", []):
        frame_name = frame.get("source_name", frame.get("source_file", "<program>"))
        frame_source = source if frame_name in ("", "<program>") else (modules.get(frame_name, "") if type(modules) is dict else "")
        frame_lines = frame_source.split("\n") if type(frame_source) is str else []
        frame_line = frame.get("line", 0)
        frame["source_line"] = frame_lines[frame_line - 1] if 0 < frame_line <= len(frame_lines) else ""
    return diagnostic


def failure(error, source, modules=None):
    return {"ok": False, "version": __version__, "mode": "preview", "proposals": [],
            "notes": [], "values": [], "diagnostics": [located(error.as_dict(source if isinstance(source, str) else ""), source, modules)]}


def contract_failure(error):
    return {"ok": False, "version": __version__, "mode": "preview", "proposals": [],
            "notes": [], "values": [], "diagnostics": error.diagnostics}


def check(source, data=None, *, contract=None, proposal_contract=None, modules=None):
    try:
        _, inputs = prepare(source, data, contract, proposal_contract, modules)
        return {"ok": True, "version": __version__, "diagnostics": [],
                "possible_inputs": inputs, "input_names_checked": data is not None,
                "proposal_contract_checked": proposal_contract is not None, "proposals_checked": False}
    except ContractFailure as error:
        return contract_failure(error)
    except SigilError as error:
        return failure(error, source, modules)
    except (RecursionError, UnicodeError):
        return failure(SigilError("E_LIMIT", "Program nesting or text encoding is invalid."), source, modules)


def run(source, data=None, *, max_steps=100000, contract=None, proposal_contract=None, modules=None):
    try:
        validate_step_limit(max_steps)
        if data is None:
            data = {}
        program, _ = prepare(source, data, contract, proposal_contract, modules)
        result = Runtime(program, data, max_steps=max_steps).execute()
        result["version"] = __version__
        if proposal_contract is not None:
            diagnostics = proposal_diagnostics(result["proposals"], proposal_contract, source)
            if diagnostics:
                raise ContractFailure(diagnostics)
        return result
    except ContractFailure as error:
        return contract_failure(error)
    except SigilError as error:
        return failure(error, source, modules)
    except (RecursionError, UnicodeError):
        return failure(SigilError("E_LIMIT", "Program nesting or text encoding is invalid."), source, modules)


def test(source, data=None, *, max_steps=100000, contract=None, proposal_contract=None, modules=None, name_filter=None, list_only=False):
    """Check a program and run only its explicit isolated test blocks."""
    try:
        validate_step_limit(max_steps)
        actual = {} if data is None else data
        program, _ = prepare(source, data, contract, proposal_contract, modules)
        if name_filter is not None and type(name_filter) is not str:
            raise SigilError("E_INPUT", "Test name_filter must be text.")
        selected = tuple(node for node in program if node.kind != "test" or name_filter is None or name_filter in node.parts[0])
        budget = TestResultBudget()
        def prepare_case(case):
            case["diagnostics"] = [located(item, source, modules) for item in case["diagnostics"]]
            return case
        if list_only:
            cases = []
            for node in selected:
                if node.kind != "test":
                    continue
                cases.append(budget.add({"name": node.parts[0], "source_name": node.token.source_name or "<program>",
                                        "ok": None, "diagnostics": [], "steps": 0}))
                if budget.stopped:
                    break
            result = {"ok": not budget.stopped, "tests": cases, "stopped_early": budget.stopped,
                      "stats": {"steps": 0, "passed": 0, "failed": int(budget.stopped)}}
        else:
            result = run_test_program(selected, actual, source, max_steps=max_steps,
                                      result_budget=budget, prepare_case=prepare_case)
        result.update(version=__version__, mode="test", total=len(result["tests"]),
                      passed=result["stats"]["passed"], failed=result["stats"]["failed"],
                      diagnostics=[item for case in result["tests"] for item in case["diagnostics"]],
                      proposals=[], notes=[], values=[])
        return bound_test_result(result)
    except ContractFailure as error:
        result = contract_failure(error)
    except SigilError as error:
        result = failure(error, source, modules)
    except (RecursionError, UnicodeError):
        result = failure(SigilError("E_LIMIT", "Program nesting or text encoding is invalid."), source, modules)
    result.update(mode="test", tests=[], total=0, passed=0, failed=0,
                  stats={"steps": 0, "passed": 0, "failed": 0})
    return bound_test_result(result)
