import argparse
import json
from pathlib import Path

from content_factory_api.app import create_app


def export_openapi_schema(output_path: Path) -> Path:
    schema = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema.")
    parser.add_argument("--output", required=True, help="Filesystem path for the schema JSON file.")
    args = parser.parse_args()
    export_openapi_schema(Path(args.output))


if __name__ == "__main__":
    main()
