import asyncio
import sys
from dataclasses import asdict
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.managers import ALL_MANAGERS_MAP  # noqa: E402
from app.managers.similarity.manager import SimilarityManager  # noqa: E402
from app.modules.logger import bastion_logger  # noqa: E402
from app.utils import text_embedding  # noqa: E402
from scripts.similarity.const import PROMPTS_EXAMPLES  # noqa: E402
from settings import get_settings  # noqa: E402

settings = get_settings()


class CreateSearchIndex:
    similarity_manager: SimilarityManager = ALL_MANAGERS_MAP["similarity"]

    async def create_index(self):
        """
        Create OpenSearch index for similarity rules with proper mapping.

        Returns:
            bool: True if index was created successfully, False otherwise
        """
        try:
            index_name = self.similarity_manager.index_name
            if await self.similarity_manager.index_exists():
                bastion_logger.info(f"Index {index_name} already exists")
                return True

            await self.similarity_manager.index_create()
            bastion_logger.info(f"Index {index_name} created successfully")
            return True

        except Exception as e:
            bastion_logger.error(f"Error creating index: {e}")
            return False

    async def upload_prompts_examples(self):
        """
        Upload example prompts to the similarity rules index.

        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            index_name = self.similarity_manager.index_name
            if not await self.similarity_manager.index_exists():
                bastion_logger.info(f"Index {index_name} does not exist. Staring to create it...")
                if not await self.create_index():
                    return False

            docs = [asdict(doc) for doc in PROMPTS_EXAMPLES]
            for doc in docs:
                doc["vector"] = text_embedding(doc["text"])
                await self.similarity_manager.index(body=doc)

            bastion_logger.info(f"Uploaded {len(docs)} example prompts to index")
            return True

        except Exception as e:
            bastion_logger.error(f"Error uploading prompts: {e}")
            return False

    async def check_index_exists(self) -> bool:
        """
        Check the status of the similarity rules index.

        Returns:
            dict: Index status information
        """
        try:
            return await self.similarity_manager.index_exists()
        except Exception as e:
            bastion_logger.error(f"Error checking index: {e}")
            return False        

    async def main(self):
        """
        Main function to create index and upload example prompts.
        """
        bastion_logger.info("Starting index creation and data upload...")
        await self.similarity_manager._activate_clients()
        try:
            status = await self.check_index_exists()
            bastion_logger.info(f"Current index exist: {'yes' if status else 'no'}")

            if not status:
                if await self.create_index():
                    bastion_logger.info("Index creation completed successfully")
                else:
                    bastion_logger.error("Failed to create index")
                    return

            if await self.upload_prompts_examples():
                bastion_logger.info("Data upload completed successfully")
            else:
                bastion_logger.error("Failed to upload data")
        finally:
            await self.similarity_manager.close_connections()


if __name__ == "__main__":
    asyncio.run(CreateSearchIndex().main())
