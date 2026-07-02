from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User, Teacher, Student
from user_progress.models import UserLevel
from tests.models import Test, ProductiveTest, ReceptiveTest
from test_histories.models import ProductiveTestHistory
from forum.models import Post


def ids(response):
    """Extract the set of test ids from a paginated list response."""
    return {row["id"] for row in response.data["results"]}


class TestOverviewBaseData(TestCase):
    """
    Shared fixtures + helpers for the test overview endpoint.

    Fixture map (created_by / type / status):
      p_pub_t1    P / P  (teacher1)  + ProductiveTest
      p_draft_t1  P / D  (teacher1)  + ProductiveTest
      p_review_t1 P / I  (teacher1)  + ProductiveTest
      p_pub_t2    P / P  (teacher2)  + ProductiveTest
      r_pub_t1    R / P  (teacher1)  + ReceptiveTest
      r_removed   R / R  (teacher1)  + ReceptiveTest
      p_orphan    P / P  (teacher1)  NO ProductiveTest  -> always excluded

    History / posts:
      student1 submission on p_pub_t1 (type S)
      student2 submission on p_pub_t1 (type S)   -> submitted(p_pub_t1) = 2
      student1 draft on p_pub_t2 (type D)
      student1 Post on p_pub_t1                  -> post_count(p_pub_t1) = 1
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("test")

        cls.level = UserLevel.objects.create(
            level_number=1, level_title="Beginner", min_xp=0, max_xp=100
        )

        # Users
        cls.admin = User.objects.create_user(
            username="admin1", email="admin1@x.com", password="pw", role="A", status="V"
        )
        cls.teacher1_user = User.objects.create_user(
            username="teacher1", email="t1@x.com", password="pw", role="T", status="V"
        )
        cls.teacher2_user = User.objects.create_user(
            username="teacher2", email="t2@x.com", password="pw", role="T", status="V"
        )
        cls.student1_user = User.objects.create_user(
            username="student1", email="s1@x.com", password="pw", role="S", status="V"
        )
        cls.student2_user = User.objects.create_user(
            username="student2", email="s2@x.com", password="pw", role="S", status="V"
        )

        cls.teacher1 = Teacher.objects.create(
            user=cls.teacher1_user,
            current_workplace="School A",
            experience_year=1,
            introduction="",
        )
        cls.teacher2 = Teacher.objects.create(
            user=cls.teacher2_user,
            current_workplace="School B",
            experience_year=1,
            introduction="",
        )
        cls.student1 = Student.objects.create(user=cls.student1_user, level=cls.level)
        cls.student2 = Student.objects.create(user=cls.student2_user, level=cls.level)

        def make_test(title, ttype, skill, status, teacher, level="B1"):
            return Test.objects.create(
                title=title,
                type=ttype,
                skill=skill,
                level=level,
                time=30,
                description="desc",
                status=status,
                created_by=teacher,
            )

        cls.p_pub_t1 = make_test("P pub t1", "P", "W", "P", cls.teacher1)
        cls.p_draft_t1 = make_test("P draft t1", "P", "W", "D", cls.teacher1)
        cls.p_review_t1 = make_test("P review t1", "P", "S", "I", cls.teacher1, level="B2")
        cls.p_pub_t2 = make_test("P pub t2", "P", "W", "P", cls.teacher2)
        cls.r_pub_t1 = make_test("R pub t1", "R", "R", "P", cls.teacher1, level="A2")
        cls.r_removed = make_test("R removed", "R", "R", "R", cls.teacher1, level="A1")
        cls.p_orphan = make_test("P orphan", "P", "W", "P", cls.teacher1)

        for t in [cls.p_pub_t1, cls.p_draft_t1, cls.p_review_t1, cls.p_pub_t2]:
            ProductiveTest.objects.create(test=t, format="A")
        for t in [cls.r_pub_t1, cls.r_removed]:
            ReceptiveTest.objects.create(test=t, total_score=10)

        now = timezone.now()
        # student1 + student2 submitted p_pub_t1
        h1 = ProductiveTestHistory.objects.create(
            student=cls.student1,
            productive_test=cls.p_pub_t1.productive_test,
            type="S",
            attempt=1,
            start_time=now,
        )
        ProductiveTestHistory.objects.create(
            student=cls.student2,
            productive_test=cls.p_pub_t1.productive_test,
            type="S",
            attempt=1,
            start_time=now,
        )
        # student1 has a draft on p_pub_t2
        ProductiveTestHistory.objects.create(
            student=cls.student1,
            productive_test=cls.p_pub_t2.productive_test,
            type="D",
            attempt=1,
            start_time=now,
        )
        # student1 posted on p_pub_t1 (via submission history h1)
        Post.objects.create(
            productive_test_history=h1, title="my post", description="hello"
        )

    def setUp(self):
        self.client = APIClient()

    def auth(self, user):
        self.client.force_authenticate(user=user)


class AnonymousVisibilityTests(TestOverviewBaseData):
    def test_anonymous_sees_only_published_with_detail(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 3)
        self.assertEqual(
            ids(res), {self.p_pub_t1.id, self.p_pub_t2.id, self.r_pub_t1.id}
        )

    def test_orphan_never_returned(self):
        res = self.client.get(self.url)
        self.assertNotIn(self.p_orphan.id, ids(res))

    def test_anonymous_non_published_status_forbidden(self):
        res = self.client.get(self.url, {"status": "D"})
        self.assertEqual(res.status_code, 403)

    def test_default_ordering_created_at_desc(self):
        res = self.client.get(self.url)
        created = [row["created_at"] for row in res.data["results"]]
        self.assertEqual(created, sorted(created, reverse=True))


class StudentVisibilityTests(TestOverviewBaseData):
    def test_student_sees_only_published(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url)
        self.assertEqual(
            ids(res), {self.p_pub_t1.id, self.p_pub_t2.id, self.r_pub_t1.id}
        )

    def test_student_non_published_status_forbidden(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"status": "R"})
        self.assertEqual(res.status_code, 403)

    def test_my_progress_completed(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_progress": "completed"})
        self.assertEqual(ids(res), {self.p_pub_t1.id})

    def test_my_progress_draft(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_progress": "draft"})
        self.assertEqual(ids(res), {self.p_pub_t2.id})

    def test_my_progress_none(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_progress": "none"})
        self.assertEqual(ids(res), {self.r_pub_t1.id})

    def test_my_progress_requires_student(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"my_progress": "completed"})
        self.assertEqual(res.status_code, 403)

    def test_progress_status_field(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"progress_status": "true"})
        by_id = {row["id"]: row for row in res.data["results"]}
        self.assertEqual(by_id[self.p_pub_t1.id]["progress_status"], "completed")
        self.assertEqual(by_id[self.p_pub_t2.id]["progress_status"], "draft")
        self.assertEqual(by_id[self.r_pub_t1.id]["progress_status"], "none")

    def test_progress_status_absent_when_not_requested(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url)
        for row in res.data["results"]:
            self.assertNotIn("progress_status", row)


class AnnotationFieldTests(TestOverviewBaseData):
    def test_submitted_field(self):
        res = self.client.get(self.url, {"submitted": "true"})
        by_id = {row["id"]: row for row in res.data["results"]}
        self.assertEqual(by_id[self.p_pub_t1.id]["submitted"], 2)
        self.assertEqual(by_id[self.p_pub_t2.id]["submitted"], 0)
        self.assertEqual(by_id[self.r_pub_t1.id]["submitted"], 0)

    def test_submitted_absent_when_not_requested(self):
        res = self.client.get(self.url)
        for row in res.data["results"]:
            self.assertNotIn("submitted", row)

    def test_post_count_field(self):
        res = self.client.get(self.url, {"post_count": "true"})
        by_id = {row["id"]: row for row in res.data["results"]}
        self.assertEqual(by_id[self.p_pub_t1.id]["post_count"], 1)
        self.assertEqual(by_id[self.p_pub_t2.id]["post_count"], 0)
        self.assertEqual(by_id[self.r_pub_t1.id]["post_count"], 0)

    def test_ordering_by_submitted(self):
        res = self.client.get(self.url, {"ordering": "-submitted"})
        # p_pub_t1 (2 submissions) should come first
        self.assertEqual(res.data["results"][0]["id"], self.p_pub_t1.id)


class TeacherVisibilityTests(TestOverviewBaseData):
    def test_teacher_default_visibility(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url)
        self.assertEqual(
            ids(res),
            {
                self.p_pub_t1.id,
                self.p_draft_t1.id,
                self.p_review_t1.id,
                self.p_pub_t2.id,
                self.r_pub_t1.id,
            },
        )

    def test_mine_true(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"mine": "true"})
        self.assertEqual(
            ids(res),
            {
                self.p_pub_t1.id,
                self.p_draft_t1.id,
                self.p_review_t1.id,
                self.r_pub_t1.id,
            },
        )

    def test_mine_false(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"mine": "false"})
        self.assertEqual(ids(res), {self.p_pub_t2.id})

    def test_mine_false_status_draft_forbidden(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"mine": "false", "status": "D"})
        self.assertEqual(res.status_code, 403)

    def test_teacher_status_removed_forbidden(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"status": "R"})
        self.assertEqual(res.status_code, 403)

    def test_mine_requires_teacher(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"mine": "true"})
        self.assertEqual(res.status_code, 403)

    def test_mine_requires_auth(self):
        res = self.client.get(self.url, {"mine": "true"})
        self.assertEqual(res.status_code, 403)


class AdminVisibilityTests(TestOverviewBaseData):
    def test_admin_sees_all_including_removed(self):
        self.auth(self.admin)
        res = self.client.get(self.url)
        self.assertEqual(
            ids(res),
            {
                self.p_pub_t1.id,
                self.p_draft_t1.id,
                self.p_review_t1.id,
                self.p_pub_t2.id,
                self.r_pub_t1.id,
                self.r_removed.id,
            },
        )

    def test_admin_filter_removed(self):
        self.auth(self.admin)
        res = self.client.get(self.url, {"status": "R"})
        self.assertEqual(ids(res), {self.r_removed.id})


class MyPostsFilterTests(TestOverviewBaseData):
    def test_my_posts_true_returns_tests_student_posted_on(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_posts": "true"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ids(res), {self.p_pub_t1.id})

    def test_my_posts_true_excludes_receptive(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_posts": "true"})
        self.assertNotIn(self.r_pub_t1.id, ids(res))

    def test_my_posts_false_returns_all_productive(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_posts": "false"})
        # false = all Productive tests (equivalent to type=P), regardless of posts;
        # tests the student HAS posted on are still included, receptive excluded.
        self.assertEqual(ids(res), {self.p_pub_t1.id, self.p_pub_t2.id})

    def test_my_posts_false_excludes_receptive(self):
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_posts": "false"})
        self.assertNotIn(self.r_pub_t1.id, ids(res))

    def test_my_posts_true_empty_for_student_without_posts(self):
        self.auth(self.student2_user)
        res = self.client.get(self.url, {"my_posts": "true"})
        self.assertEqual(res.data["count"], 0)

    def test_my_posts_false_for_student_without_posts(self):
        self.auth(self.student2_user)
        res = self.client.get(self.url, {"my_posts": "false"})
        self.assertEqual(ids(res), {self.p_pub_t1.id, self.p_pub_t2.id})

    def test_my_posts_requires_student(self):
        self.auth(self.teacher1_user)
        res = self.client.get(self.url, {"my_posts": "true"})
        self.assertEqual(res.status_code, 403)

    def test_my_posts_requires_auth(self):
        res = self.client.get(self.url, {"my_posts": "true"})
        self.assertEqual(res.status_code, 403)

    def test_my_posts_ignored_when_not_boolean(self):
        # An unrelated value behaves as if the param was not supplied.
        self.auth(self.student1_user)
        res = self.client.get(self.url, {"my_posts": "maybe"})
        self.assertEqual(
            ids(res), {self.p_pub_t1.id, self.p_pub_t2.id, self.r_pub_t1.id}
        )
