#!/usr/bin/env python3
import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from factoryos import create_app
from factoryos.core.storage import (
    ensure_storage_structure,
    ensure_tool_error_structure,
    ensure_tool_structure,
    is_managed_storage_path,
    resolve_stored_file,
    storage_root,
    stored_relative_path,
    temp_tool_error_image_folder,
    tool_category_folder,
    tool_error_revision_folder,
)
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError, ToolErrorImage


LEGACY_TOOL_FOLDERS = {
    "images": "images",
    "documents": "documents",
    "service": "service",
    "history": "history",
}


class StorageMigration:

    def __init__(self, apply_changes=False):
        self.apply_changes = apply_changes
        self.copied = 0
        self.updated = 0
        self.missing = 0
        self.created_folders = 0
        self.untracked = 0
        self.source_cache = {}
        self.migrated_sources = set()
        self.sources_to_delete = set()

    def _candidate(self, destination, filename, source):
        destination = Path(destination)
        name = Path(filename).name or "Datei"
        candidate = destination / name
        counter = 2

        while candidate.exists():
            try:
                if (
                    candidate.is_file()
                    and candidate.stat().st_size == source.stat().st_size
                    and filecmp.cmp(candidate, source, shallow=False)
                ):
                    return candidate
            except OSError:
                pass

            candidate = destination / (
                f"{Path(name).stem}_{counter}{Path(name).suffix}"
            )
            counter += 1

        return candidate

    def _copy(self, source, destination):
        source = Path(source).resolve()
        destination = Path(destination).resolve()
        cache_key = (str(source), str(destination))

        if cache_key in self.source_cache:
            return self.source_cache[cache_key]

        if not source.is_file():
            self.missing += 1
            print(f"FEHLT: {source}")
            return None

        target = self._candidate(destination, source.name, source)
        relative = stored_relative_path(target)

        print(f"DATEI: {source} -> {target}")

        if self.apply_changes:
            destination.mkdir(parents=True, exist_ok=True)

            if not target.exists():
                shutil.copy2(source, target)

            if (
                target.stat().st_size != source.stat().st_size
                or not filecmp.cmp(target, source, shallow=False)
            ):
                raise IOError(f"Dateiprüfung fehlgeschlagen: {target}")

            if not source.is_relative_to(storage_root()):
                self.sources_to_delete.add(source)

        self.source_cache[cache_key] = relative
        self.migrated_sources.add(str(source))
        self.copied += 1
        return relative

    def _migrate_model_path(self, model, destination):
        old_path = (model.image_path or "").replace("\\", "/")

        if not old_path:
            return

        try:
            source = resolve_stored_file(old_path)
        except ValueError:
            self.missing += 1
            print(f"UNGÜLTIGER PFAD: {old_path}")
            return

        if is_managed_storage_path(old_path) and source.is_file():
            return

        new_path = self._copy(source, destination)

        if new_path and new_path != old_path:
            print(f"DATENBANK: {old_path} -> {new_path}")

            if self.apply_changes:
                model.image_path = new_path

            self.updated += 1

    def _copy_tree(self, source_root, destination_root):
        source_root = Path(source_root)

        if not source_root.is_dir():
            return

        for source in source_root.rglob("*"):
            if not source.is_file():
                continue

            relative_parent = source.relative_to(source_root).parent
            self._copy(
                source,
                Path(destination_root) / relative_parent,
            )

    def migrate_tools(self):
        for tool in Tool.query.order_by(Tool.tool_no.asc()).all():
            print(f"\nWERKZEUG: {tool.tool_no}")

            if self.apply_changes:
                ensure_tool_structure(tool.tool_no)

            self.created_folders += 1

            for image in tool.images or []:
                self._migrate_model_path(
                    image,
                    tool_category_folder(tool.tool_no, "images"),
                )

            legacy_base = Path(
                PROJECT_ROOT,
                "factoryos",
                "static",
                "uploads",
                "tools",
                str(tool.tool_no),
            )

            for old_name, category in LEGACY_TOOL_FOLDERS.items():
                self._copy_tree(
                    legacy_base / old_name,
                    tool_category_folder(tool.tool_no, category),
                )

    def migrate_tool_errors(self):
        errors = ToolError.query.order_by(
            ToolError.error_no.asc(),
            ToolError.revision.asc(),
        ).all()

        for error in errors:
            if not error.tool:
                print(f"FEHLERMELDUNG OHNE WERKZEUG: {error.id}")
                continue

            print(
                f"\nFEHLERMELDUNG: {error.error_no} "
                f"Revision {error.revision} / {error.tool.tool_no}"
            )

            if self.apply_changes:
                ensure_tool_error_structure(
                    error.tool.tool_no,
                    error.error_no,
                    error.revision,
                )

            destination = tool_error_revision_folder(
                error.tool.tool_no,
                error.error_no,
                error.revision,
            ) / "Bilder"

            for image in error.images or []:
                self._migrate_model_path(image, destination)

        temporary_images = ToolErrorImage.query.filter(
            ToolErrorImage.tool_error_id.is_(None)
        ).all()

        for image in temporary_images:
            if not image.temp_id:
                continue

            if self.apply_changes:
                destination = temp_tool_error_image_folder(image.temp_id)
            else:
                destination = storage_root().joinpath(
                    "Stammdaten",
                    "Werkzeuge",
                    "_Unzugeordnet",
                    "Werkzeugfehlermeldungen",
                    "_Temp",
                    str(image.temp_id),
                    "Bilder",
                )

            self._migrate_model_path(image, destination)

        legacy_error_folder = Path(
            PROJECT_ROOT,
            "factoryos",
            "static",
            "uploads",
            "tool_errors",
        )
        old_stock = storage_root().joinpath(
            "Stammdaten",
            "Werkzeuge",
            "_Unzugeordnet",
            "Werkzeugfehlermeldungen",
            "_Altbestand",
        )

        if legacy_error_folder.is_dir():
            for source in legacy_error_folder.rglob("*"):
                if not source.is_file():
                    continue

                if str(source.resolve()) in self.migrated_sources:
                    continue

                self._copy(source, old_stock)
                self.untracked += 1

    def _remove_legacy_sources(self):
        for source in sorted(
            self.sources_to_delete,
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                source.unlink()
            except FileNotFoundError:
                pass
            except OSError as error:
                print(f"WARNUNG: Altdatei blieb erhalten: {source}: {error}")

        legacy_roots = [
            PROJECT_ROOT / "factoryos" / "static" / "uploads" / "tools",
            PROJECT_ROOT / "factoryos" / "static" / "uploads" / "tool_errors",
        ]

        for root in legacy_roots:
            if not root.exists():
                continue

            for directory, _, _ in os.walk(root, topdown=False):
                try:
                    Path(directory).rmdir()
                except OSError:
                    pass

    def run(self):
        if self.apply_changes:
            ensure_storage_structure()

        self.migrate_tools()
        self.migrate_tool_errors()

        if self.apply_changes:
            db.session.commit()
            self._remove_legacy_sources()
        else:
            db.session.rollback()

        print("\nERGEBNIS")
        print(f"Werkzeugordner: {self.created_folders}")
        print(f"Kopierte Dateien: {self.copied}")
        print(f"Aktualisierte Datenbankpfade: {self.updated}")
        print(f"Unzugeordneter Altbestand: {self.untracked}")
        print(f"Fehlende Dateien: {self.missing}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Migriert FactoryOS-Dateien aus static/uploads in die "
            "strukturierte instance/storage-Ablage."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Migration wirklich ausführen (ohne Option nur Vorschau).",
    )
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        mode = "AUSFÜHREN" if args.apply else "VORSCHAU"
        print(f"FactoryOS Speichermigration: {mode}")
        print(f"Ziel: {storage_root()}")
        StorageMigration(apply_changes=args.apply).run()


if __name__ == "__main__":
    main()
