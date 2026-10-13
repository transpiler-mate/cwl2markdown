# Copyright 2026 Terradue
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import Mock

from cwl_utils.parser import cwl_v1_2
from pydantic import AnyUrl
from transpiler_mate.api import (
    AuthorRole,
    ContributorRole,
    CreativeWork,
    Organization,
    Person,
    SoftwareApplication,
    TranspilerContext,
    TranspilerContextResolver,
)

from cwl2markdown.plugin import (
    CWL2MarkdownOptions,
    cwl2markdown,
    normalize_author,
    normalize_contributor,
    nullable,
    type_to_string,
)

if TYPE_CHECKING:
    from pathlib import Path


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


def test_plugin_renders_markdown_without_jinja_filename_suffix(tmp_path: Path) -> None:
    workflow = cwl_v1_2.Workflow(
        id="example-workflow", cwlVersion="v1.2", inputs=[], outputs=[], steps=[]
    )
    metadata = SoftwareApplication(
        name="Example application",
        description="A minimal workflow for documentation.",
        date_created=date(2026, 1, 1),
        license=CreativeWork(name="Apache License 2.0", identifier="Apache-2.0"),
        software_version="1.0.0",
        software_help=[],
        publisher=Organization(name="Example Organization"),
        author=_person("Alice"),
    )
    context = TranspilerContext(
        source=AnyUrl("https://example.org/workflow.cwl"),
        metadata=metadata,
        document={workflow.id: workflow},
        resolver=Mock(spec=TranspilerContextResolver),
    )
    output_directory = tmp_path / "documentation"

    cwl2markdown.execute(context, CWL2MarkdownOptions(output=output_directory))

    output_file = output_directory / "example-workflow.md"
    assert output_file.is_file()
    assert not (output_directory / "example-workflow.md.jinja").exists()
    markdown = output_file.read_text()
    assert "# Example application v1.0.0" in markdown
    assert "A minimal workflow for documentation." in markdown
    assert "## example-workflow" in markdown
    assert "[Workflow](https://www.commonwl.org/v1.2/Workflow.html#Workflow)" in markdown
