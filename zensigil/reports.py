"""Bounded JUnit-style XML from completed test results; never reads or writes files."""
from collections import Counter
import json
import xml.etree.ElementTree as ET

MAX_REPORT_CASES = 10000
MAX_REPORT_BYTES = 8 * 1024 * 1024


class _XMLText:
    def __init__(self):
        self.size = 1024  # Reserve the document/suite framing.

    def reserve(self, size):
        self.size += size
        if self.size > MAX_REPORT_BYTES:
            raise ValueError("JUnit report exceeds the 8 MiB report limit.")

    def clean(self, value):
        """Replace invalid XML 1.0 characters, charging escaped UTF-8 size."""
        if not isinstance(value, str):
            raise ValueError("JUnit report names and diagnostic text must be strings.")
        result = []
        for char in value:
            point = ord(char)
            if not (point in (9, 10, 13) or 0x20 <= point <= 0xD7FF
                    or 0xE000 <= point <= 0xFFFD or 0x10000 <= point <= 0x10FFFF):
                char = "\ufffd"
            # Conservatively covers attribute escaping, including newlines.
            self.reserve(6 if char in "\"'" else 5 if char in "&\t\n\r"
                         else 4 if char in "<>" else len(char.encode("utf-8")))
            result.append(char)
        return "".join(result)


def _diagnostics(value):
    if type(value) is not list or any(type(item) is not dict for item in value):
        raise ValueError("Test diagnostics must be a list of objects.")
    for diagnostic in value:
        if type(diagnostic.get("code", "E_TEST")) is not str or type(diagnostic.get("message", "")) is not str:
            raise ValueError("Diagnostic code and message must be text.")
    return value


def _diagnostic_key(diagnostic):
    # CLI aggregates repeat case diagnostics with one added suite-source field.
    try:
        return json.dumps({key: value for key, value in diagnostic.items() if key != "project_source"},
                          sort_keys=True, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise ValueError("JUnit diagnostics must contain bounded JSON-compatible data.")


def _details(diagnostic):
    location = diagnostic.get("source_file", diagnostic.get("source_name", diagnostic.get("project_source", "<program>")))
    position = f"{location}:{diagnostic.get('line', 1)}:{diagnostic.get('column', 1)}"
    text = f"{position} {diagnostic.get('code', 'E_TEST')}: {diagnostic.get('message', '')}"
    for field, label in (("data_path", "Input"), ("output_path", "Output")):
        if field in diagnostic:
            text += f"\n{label}: {diagnostic[field]}"
    if diagnostic.get("source_line"):
        text += "\n" + str(diagnostic["source_line"])
    frames = diagnostic.get("call_trace", [])
    if type(frames) is list:
        for frame in frames[:64]:
            if type(frame) is dict:
                text += (f"\nCalled {frame.get('function', '<function>')} at "
                         f"{frame.get('source_file', frame.get('source_name', '<program>'))}:"
                         f"{frame.get('line', 1)}:{frame.get('column', 1)}")
    return text


def junit_xml(test_result, suite_name="ZenSigil"):
    """Serialize an executed test result; list-only results raise ValueError.

    Assertion diagnostics (E_REQUIRE) are failures; other failing cases and
    errors before test discovery are errors. No duration or timestamp is invented.
    Counters are derived from cases, not trusted from caller-provided totals.
    """
    if type(test_result) is not dict or type(test_result.get("ok")) is not bool:
        raise ValueError("A test result must be an object with a boolean ok field.")
    if test_result.get("listed") is True:
        raise ValueError("JUnit reports require executed tests, not a list-only result.")
    cases = test_result.get("tests", [])
    if type(cases) is not list or len(cases) > MAX_REPORT_CASES:
        raise ValueError("JUnit reports allow at most 10,000 test cases.")
    top_diagnostics = _diagnostics(test_result.get("diagnostics", []))
    budget = _XMLText()
    suite_label = budget.clean(suite_name)
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name=suite_label)
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    represented = Counter()

    def add_case(name, diagnostics, failed=False, source="", source_context="", force_error=False):
        counts["tests"] += 1
        if counts["tests"] > MAX_REPORT_CASES:
            raise ValueError("JUnit reports allow at most 10,000 test cases.")
        budget.reserve(256)
        classname = suite_name
        if source:
            classname += ":" + source
            if source_context and source_context != source:
                classname = suite_name + ":" + source_context + "::" + source
        attributes = {"name": budget.clean(name), "classname": budget.clean(classname)}
        if source:
            attributes["file"] = budget.clean(source)
        element = ET.SubElement(suite, "testcase", attributes)
        if failed or diagnostics:
            diagnostics = diagnostics or [{"code": "E_TEST", "message": "Test failed without a diagnostic."}]
            assertion = not force_error and all(item.get("code") == "E_REQUIRE" for item in diagnostics)
            category = "failure" if assertion else "error"
            counts["failures" if assertion else "errors"] += 1
            budget.reserve(128)
            problem = ET.SubElement(element, category,
                                    message=budget.clean(diagnostics[0].get("message", "Test failed.")),
                                    type=budget.clean(diagnostics[0].get("code", "E_TEST")))
            # Clean each diagnostic before joining, bounding accumulated report text.
            problem.text = "\n\n".join(budget.clean(_details(item)) for item in diagnostics)

    for case in cases:
        if type(case) is not dict or type(case.get("name")) is not str:
            raise ValueError("Every test case needs a text name.")
        if case.get("ok") is None:
            raise ValueError("JUnit reports require executed tests, not a list-only result.")
        if type(case["ok"]) is not bool:
            raise ValueError("Test case ok must be a boolean.")
        diagnostics = _diagnostics(case.get("diagnostics", []))
        for diagnostic in diagnostics:
            represented[_diagnostic_key(diagnostic)] += 1
        source_file = case.get("source_file", "")
        source_name = case.get("source_name", "")
        if type(source_file) is not str or type(source_name) is not str:
            raise ValueError("Test source names must be strings.")
        source = source_name if source_name and source_name != "<program>" else source_file
        add_case(case["name"], diagnostics, failed=not case["ok"], source=source,
                 source_context=source_file)

    for diagnostic in top_diagnostics:
        key = _diagnostic_key(diagnostic)
        if represented[key]:
            represented[key] -= 1
        else:
            add_case("Program check", [diagnostic], failed=True, force_error=True,
                     source=diagnostic.get("project_source", diagnostic.get("source_file", "")))
    if not test_result["ok"] and counts["failures"] + counts["errors"] == 0:
        add_case("Test run", [{"code": "E_TEST_RUN", "message": "Test run failed before a diagnostic was available."}],
                 failed=True, force_error=True)
    attributes = {key: str(value) for key, value in counts.items()}
    root.attrib.update(attributes)
    suite.attrib.update(attributes)
    rendered = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(rendered) + 1 > MAX_REPORT_BYTES:
        raise ValueError("JUnit report exceeds the 8 MiB report limit.")
    return rendered.decode("utf-8") + "\n"
