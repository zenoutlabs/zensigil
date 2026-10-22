"""Test a portable project with one work budget and explicit source identities."""
from . import (__version__, ContractFailure, contract_failure, failure, located,
               prepare)
from .errors import SigilError
from .modules import module_name
from .programs import validate_source_maps
from .testing import TestResultBudget, bound_test_result, run_test_program

MAX_BUNDLE_TESTS = 10000


def _locate(entry, source, modules, name):
    entry = located(entry, source, modules)
    if entry.get("source_name", "<program>") == "<program>":
        entry["source_name"] = name
    if entry.get("source_file") == "<program>":
        entry["source_file"] = name
    for frame in entry.get("call_trace", []):
        if frame.get("source_name", "<program>") == "<program>":
            frame["source_name"] = name
        if frame.get("source_file") == "<program>":
            frame["source_file"] = name
    return entry


def test_bundle(source, data=None, *, tests=None, modules=None, contract=None,
                proposal_contract=None, name_filter=None, list_only=False,
                max_steps=100000, source_name="<program>"):
    """Check all roots, then run each source/name once with a shared step budget.

    Tests are raw, named source files. Imports resolve only from modules. Roots
    keep separate function scopes. Input and contract checks match the test API.
    No filesystem or network access occurs here.
    """
    current_source, current_name = source, source_name
    try:
        if type(source_name) is not str or not source_name:
            raise ValueError("The entry source name must be nonempty text.")
        if source_name != "<program>":
            module_name(source_name)
        if name_filter is not None and type(name_filter) is not str:
            raise ValueError("The test name filter must be text.")
        if type(max_steps) is not int or not 1 <= max_steps <= 100000:
            raise ValueError("A bundle test budget must be from 1 to 100000 steps.")
        modules, tests = validate_source_maps(modules, tests)
        for sources in (modules, tests):
            for name, body in sources.items():
                left, right = source_name.casefold(), name.casefold()
                if source_name == name:
                    if source != body:
                        raise ValueError("The entry source name must not identify different module or test text.")
                elif left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                    raise ValueError("The entry source name must not conflict with module or test paths.")
        plans, seen = [], set()
        for name, body in [(source_name, source), *tests.items()]:
            current_source, current_name = body, name
            program, _ = prepare(body, data, contract, proposal_contract, modules)
            selected = []
            for node in program:
                if node.kind != "test":
                    selected.append(node)
                    continue
                if name_filter is not None and name_filter not in node.parts[0]:
                    continue
                origin = node.token.source_name or "<program>"
                identity = (name if origin == "<program>" else origin, node.parts[0])
                if identity in seen:
                    continue
                seen.add(identity)
                if len(seen) > MAX_BUNDLE_TESTS:
                    raise SigilError("E_TEST_LIMIT", "A bundled project allows at most 10000 selected tests.")
                selected.append(node)
            plans.append((name, body, tuple(selected)))
        cases, steps, stopped = [], 0, False
        budget = TestResultBudget()
        for name, body, program in plans:
            current_source, current_name = body, name
            selected = [node for node in program if node.kind == "test"]
            if not selected:
                continue
            def prepare_case(case):
                if case["source_name"] == "<program>":
                    case["source_name"] = name
                case["source_file"] = case["source_name"]
                case["diagnostics"] = [_locate(item, body, modules, name) for item in case["diagnostics"]]
                return case
            if list_only:
                listed = []
                for node in selected:
                    listed.append(budget.add(prepare_case({"name": node.parts[0],
                                  "source_name": node.token.source_name or "<program>",
                                  "ok": None, "diagnostics": [], "steps": 0})))
                    if budget.stopped:
                        break
                result = {"tests": listed, "stats": {"steps": 0}}
            elif steps >= max_steps:
                node = selected[0]
                error = SigilError("E_LIMIT", "Bundled project tests exhausted their shared step limit.",
                                   node.token.line, node.token.column)
                error.source_name = node.token.source_name
                result = {"tests": [budget.add(prepare_case({"name": node.parts[0],
                                     "source_name": node.token.source_name or "<program>",
                                     "ok": False, "diagnostics": [error.as_dict(body)], "steps": 0}))],
                          "stats": {"steps": 0}}
            else:
                result = run_test_program(program, {} if data is None else data, body,
                                          max_steps=max_steps - steps, result_budget=budget,
                                          prepare_case=prepare_case)
            steps += result["stats"]["steps"]
            cases.extend(result["tests"])
            if budget.stopped or any(item["code"] == "E_LIMIT" for case in result["tests"] for item in case["diagnostics"]):
                stopped = True
                break
        passed = sum(case["ok"] is True for case in cases)
        failed = sum(case["ok"] is False for case in cases)
        result = {"ok": failed == 0, "version": __version__, "mode": "test", "tests": cases,
                  "total": len(cases), "passed": passed, "failed": failed,
                  "diagnostics": [item for case in cases for item in case["diagnostics"]],
                  "proposals": [], "notes": [], "values": [],
                  "stopped_early": stopped,
                  "stats": {"steps": steps, "passed": passed, "failed": failed}}
        if list_only:
            result["listed"] = True
        return bound_test_result(result)
    except ContractFailure as error:
        result = contract_failure(error)
    except SigilError as error:
        result = failure(error, current_source, modules)
    except (ValueError, RecursionError, UnicodeError) as error:
        result = failure(SigilError("E_TEST_BUNDLE", str(error)), current_source, modules)
    for entry in result["diagnostics"]:
        _locate(entry, current_source, modules, current_name)
    result.update(mode="test", tests=[], total=0, passed=0, failed=0,
                  stats={"steps": 0, "passed": 0, "failed": 0})
    return bound_test_result(result)
