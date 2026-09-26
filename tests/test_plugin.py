from cwl_utils.parser import cwl_v1_2
from transpiler_mate.api import (
    AuthorRole,
    ContributorRole,
    Organization,
    Person,
    SoftwareApplication,
)

from cwl2markdown.plugin import normalize_author, normalize_contributor, nullable, type_to_string


def _person(given_name: str) -> Person:
    return Person(
        given_name=given_name,
        family_name="Example",
        email=f"{given_name.lower()}@example.com",
        affiliation=Organization(name="Example Organization"),
    )


def test_normalize_author_uses_software_application_models() -> None:
    person = _person("Alice")
    role = AuthorRole(role_name="Developer", author=_person("Bob"))
    metadata = SoftwareApplication.model_construct(author=[person, role])

    normalized = normalize_author(metadata)

    assert normalized == [AuthorRole(role_name="N/A", author=person), role]
    assert all(isinstance(author, AuthorRole) for author in normalized)


def test_normalize_contributor_uses_software_application_models() -> None:
    person = _person("Carol")
    role = ContributorRole(role_name="Reviewer", contributor=_person("Dan"))
    metadata = SoftwareApplication.model_construct(contributor=[person, role])

    normalized = normalize_contributor(metadata)

    assert normalized == [ContributorRole(role_name="N/A", contributor=person), role]
    assert all(isinstance(contributor, ContributorRole) for contributor in normalized)


def test_normalize_contributor_handles_missing_contributors() -> None:
    metadata = SoftwareApplication.model_construct(contributor=None)

    assert normalize_contributor(metadata) == []


def test_type_to_string_resolves_schema_references() -> None:
    schema = cwl_v1_2.InputEnumSchema(
        type_="enum",
        name="https://example.org/types#Choice",
        symbols=["https://example.org/types/first", "https://example.org/types/second"],
    )
    workflow = cwl_v1_2.Workflow(
        inputs=[],
        outputs=[],
        steps=[],
        requirements=[cwl_v1_2.SchemaDefRequirement(types=[schema])],
    )

    assert type_to_string(schema.name, workflow) == (
        "[enum](https://www.commonwl.org/v1.2/Workflow.html#InputEnumSchema):"
        "<ul><li>`first`</li><li>`second`</li></ul>"
    )
    assert type_to_string("https://example.org/types#Missing", workflow) == (
        "[Missing](https://example.org/types#Missing)"
    )


def test_type_to_string_renders_nested_arrays_and_unions() -> None:
    workflow = cwl_v1_2.Workflow(inputs=[], outputs=[], steps=[])
    schema = cwl_v1_2.InputArraySchema(type_="array", items=["null", "File"])

    assert type_to_string(schema, workflow) == (
        "`array` of One of:<ul>"
        "<li>[null](https://www.commonwl.org/v1.2/Workflow.html#CWLType)</li>"
        "<li>[File](https://www.commonwl.org/v1.2/Workflow.html#File)</li></ul>"
    )
    assert nullable(schema)
    assert not nullable(cwl_v1_2.InputArraySchema(type_="array", items="File"))


def test_type_to_string_renders_python_unions() -> None:
    workflow = cwl_v1_2.Workflow(inputs=[], outputs=[], steps=[])

    assert type_to_string(str | int, workflow) == (
        "One of:<ul>"
        "<li>[str](https://www.commonwl.org/v1.2/Workflow.html#CWLType)</li>"
        "<li>[int](https://www.commonwl.org/v1.2/Workflow.html#CWLType)</li></ul>"
    )
