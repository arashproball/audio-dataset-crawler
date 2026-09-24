from src.database.connection import SessionLocal
from src.export.dataset_exporter import DatasetExporter


with SessionLocal() as session:
    exporter = DatasetExporter(session)

    exporter.export_csv(
        "data/audio_dataset.csv"
    )

    exporter.export_parquet(
        "data/audio_dataset.parquet"
    )

print("Dataset exported successfully.")