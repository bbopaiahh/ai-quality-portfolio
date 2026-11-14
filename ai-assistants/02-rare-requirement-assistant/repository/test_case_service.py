from typing import List

from models.test_case import TestCase
from repository.test_case_repository import TestCaseRepository


class TestCaseService:
    """
    Service layer responsible for converting generated test-case
    data into TestCase repository objects.

    This keeps repository logic separate from the LLM generation
    and Streamlit UI layers.
    """

    def __init__(
        self,
        repository: TestCaseRepository | None = None,
    ):
        self.repository = (
            repository
            or TestCaseRepository()
        )

    def save_test_cases(
        self,
        test_cases: List[TestCase],
    ) -> List[TestCase]:
        """
        Save a list of TestCase objects into the repository.
        """

        if not test_cases:
            return []

        return self.repository.save_many(
            test_cases
        )

    def get_test_case(
        self,
        test_case_id: str,
    ) -> TestCase | None:
        """
        Retrieve the latest version of a test case.
        """

        return self.repository.get_by_id(
            test_case_id
        )

    def get_all_test_cases(
        self,
    ) -> List[TestCase]:
        """
        Retrieve all latest test-case versions.
        """

        return self.repository.get_all()

    def search_test_cases(
        self,
        query: str,
    ) -> List[TestCase]:
        """
        Search the repository.
        """

        return self.repository.search(
            query
        )

    def count(self) -> int:
        """
        Return the number of unique test cases.

        Each stable Test Case ID is counted once, regardless
        of how many historical versions are stored.
        """

        return len(
            self.repository.get_all()
        )

    def count_records(self) -> int:
        """
        Return the total number of stored repository records,
        including historical versions.
        """

        return self.repository.count()
