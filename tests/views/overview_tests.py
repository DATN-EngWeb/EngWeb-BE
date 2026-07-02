from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import PermissionDenied
import django_filters
from django.db.models import Q, Exists, OuterRef, Count, Case, When, IntegerField, Value

from ..models import Test
from ..serializers.test import TestSerializer
from ..permissions import IsTeacher
from ..filters import TestFilter
from accounts.models import Teacher, Student
from test_histories.models import ProductiveTestHistory, ReceptiveTestHistory

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import serializers


class TestPagination(PageNumberPagination):
    """
    Pagination class for Tests API
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TestOverviewListCreateView(generics.ListCreateAPIView):
    """
    GET: List all tests (overview) with filtering and pagination
    POST: Create a new test (Teacher only)
    """

    queryset = (
        Test.objects.all()
        .select_related("created_by__user", "receptive_test", "productive_test")
        .order_by("-created_at")
    )
    serializer_class = TestSerializer
    pagination_class = TestPagination
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        OrderingFilter,
    ]
    filterset_class = TestFilter
    ordering_fields = ["created_at", "updated_at", "title", "submitted"]
    ordering = ["-created_at"]

    def get_permissions(self):
        """
        GET: Allow any user
        POST: Only teachers
        """
        if self.request.method == "POST":
            return [IsTeacher()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """
        Build the test overview queryset by composing independent filter steps.

        Order matters only for the auth/permission checks (a request that misuses
        several restricted params fails on the first one), so the steps run in the
        same order as before the refactor:
        1. Drop overview-only tests missing their detail record.
        2. `mine`      (teacher-only filter).
        3. `my_progress` (student-only filter).
        4. `my_posts`  (student-only filter).
        5. Role-based visibility + `status` policy.
        6. `submitted` / `post_count` annotations (only when requested).
        """
        queryset = super().get_queryset()
        queryset = self._exclude_overview_only(queryset)
        queryset = self._apply_mine_filter(queryset)
        queryset = self._apply_my_progress_filter(queryset)
        queryset = self._apply_my_posts_filter(queryset)
        queryset = self._apply_visibility_policy(queryset)
        queryset = self._annotate_submitted(queryset)
        queryset = self._annotate_post_count(queryset)
        return queryset

    def _exclude_overview_only(self, queryset):
        """Exclude overview-only tests that do not have the matching detail record."""
        return queryset.filter(
            Q(type="P", productive_test__isnull=False)
            | Q(type="R", receptive_test__isnull=False)
        )

    def _apply_mine_filter(self, queryset):
        """
        Handle the teacher-only `mine` filter.
        - mine=true: tests created by the current teacher
        - mine=false: tests NOT created by the current teacher
        - mine not provided: no change
        Raises PermissionDenied if a non-teacher (or anonymous user) uses it.
        """
        mine = self.request.query_params.get("mine", "").lower()
        if mine not in ["true", "false"]:
            return queryset

        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                detail="Authentication required to use 'mine' parameter."
            )

        try:
            teacher = Teacher.objects.get(user=self.request.user)
        except Teacher.DoesNotExist:
            raise PermissionDenied(
                detail="Only teachers can use 'mine' parameter to filter tests."
            )

        if mine == "true":
            return queryset.filter(created_by=teacher)
        return queryset.exclude(created_by=teacher)

    def _apply_my_progress_filter(self, queryset):
        """
        Handle the student-only `my_progress` filter (completed/draft/none).
        Each branch matches Productive and Receptive tests against their own
        history table so a test only ever matches through its own type.
        Raises PermissionDenied if a non-student (or anonymous user) uses it.
        """
        my_progress = self.request.query_params.get("my_progress", "").lower()
        if my_progress not in ["completed", "draft", "none"]:
            return queryset

        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                detail="Authentication required to use 'my_progress' parameter."
            )

        try:
            student = Student.objects.get(user=self.request.user)
        except Student.DoesNotExist:
            raise PermissionDenied(
                detail="Only students can use 'my_progress' parameter to filter tests."
            )

        if my_progress == "completed":
            # Tests with submission but NO draft (fully completed)
            productive_submission_exists = ProductiveTestHistory.objects.filter(
                student=student, productive_test__test=OuterRef("pk"), type="S"
            )
            productive_draft_exists = ProductiveTestHistory.objects.filter(
                student=student, productive_test__test=OuterRef("pk"), type="D"
            )
            productive_completed = Q(Exists(productive_submission_exists)) & ~Q(
                Exists(productive_draft_exists)
            )

            receptive_submission_exists = ReceptiveTestHistory.objects.filter(
                student=student, receptive_test__test=OuterRef("pk"), type="S"
            )
            receptive_draft_exists = ReceptiveTestHistory.objects.filter(
                student=student, receptive_test__test=OuterRef("pk"), type="D"
            )
            receptive_completed = Q(Exists(receptive_submission_exists)) & ~Q(
                Exists(receptive_draft_exists)
            )

            return queryset.filter(
                (Q(type="P") & productive_completed)
                | (Q(type="R") & receptive_completed)
            )

        if my_progress == "draft":
            # Tests with a draft (regardless of submission status)
            productive_draft_exists = ProductiveTestHistory.objects.filter(
                student=student, productive_test__test=OuterRef("pk"), type="D"
            )
            productive_draft = Q(Exists(productive_draft_exists))

            receptive_draft_exists = ReceptiveTestHistory.objects.filter(
                student=student, receptive_test__test=OuterRef("pk"), type="D"
            )
            receptive_draft = Q(Exists(receptive_draft_exists))

            return queryset.filter(
                (Q(type="P") & productive_draft) | (Q(type="R") & receptive_draft)
            )

        # my_progress == "none": tests with no history at all
        productive_history_exists = ProductiveTestHistory.objects.filter(
            student=student, productive_test__test=OuterRef("pk")
        )
        productive_no_history = ~Q(Exists(productive_history_exists))

        receptive_history_exists = ReceptiveTestHistory.objects.filter(
            student=student, receptive_test__test=OuterRef("pk")
        )
        receptive_no_history = ~Q(Exists(receptive_history_exists))

        return queryset.filter(
            (Q(type="P") & productive_no_history)
            | (Q(type="R") & receptive_no_history)
        )

    def _apply_my_posts_filter(self, queryset):
        """
        Handle the student-only `my_posts` filter (forum posts). Forum posts only
        exist for Productive tests, so both branches are scoped to type='P'.
        - my_posts=true: Productive tests where the current student has at least
          one forum post.
        - my_posts=false: all Productive tests, regardless of whether the student
          has posted (equivalent to filtering type='P').
        - my_posts not provided: no change.
        Raises PermissionDenied if a non-student (or anonymous user) uses it.
        """
        my_posts = self.request.query_params.get("my_posts", "").lower()
        if my_posts not in ["true", "false"]:
            return queryset

        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                detail="Authentication required to use 'my_posts' parameter."
            )

        try:
            student = Student.objects.get(user=self.request.user)
        except Student.DoesNotExist:
            raise PermissionDenied(
                detail="Only students can use 'my_posts' parameter to filter tests."
            )

        if my_posts == "false":
            # All Productive tests, no filtering by whether the student has posted.
            return queryset.filter(type="P")

        # true: Productive tests where the current student has at least one post.
        # Import here to avoid a circular import at module load time.
        from forum.models import Post

        my_post_exists = Post.objects.filter(
            productive_test_history__student=student,
            productive_test_history__productive_test__test=OuterRef("pk"),
        )
        # Exists() already restricts to Productive tests that have posts.
        return queryset.filter(Exists(my_post_exists))

    def _apply_visibility_policy(self, queryset):
        """
        Apply role-based visibility and validate the `status` filter.
        - Anonymous/Student: only published tests; may only filter status='P'.
        - Teacher: own tests can be P/D/I, others only P/I; cannot filter 'R',
          and cannot filter other teachers' drafts (mine=false + status=D).
        - Admin: all statuses, no extra filtering.
        """
        mine = self.request.query_params.get("mine", "").lower()
        status_filter = self.request.query_params.get("status", "")

        if not self.request.user.is_authenticated:
            if status_filter and status_filter != "P":
                raise PermissionDenied(
                    detail="Anonymous users can only filter by status 'P' (Published)."
                )
            return queryset.filter(status="P")

        role = getattr(self.request.user, "role", None)

        if role == "S":
            if status_filter and status_filter != "P":
                raise PermissionDenied(
                    detail="Students can only filter by status 'P' (Published)."
                )
            return queryset.filter(status="P")

        if role == "T":
            if status_filter == "R":
                raise PermissionDenied(
                    detail="Only admin users can filter by status 'R' (Removed)."
                )

            if status_filter and status_filter not in ["P", "I", "D"]:
                raise PermissionDenied(
                    detail="Teachers can only filter by status 'P', 'I', or 'D'."
                )

            if mine == "false" and status_filter == "D":
                raise PermissionDenied(
                    detail="Teachers cannot filter draft tests of other teachers."
                )

            teacher = getattr(self.request.user, "teacher", None)
            if not teacher:
                raise PermissionDenied(
                    detail="Teacher profile not found for this account."
                )

            return queryset.filter(
                Q(created_by=teacher, status__in=["P", "D", "I"])
                | (~Q(created_by=teacher) & Q(status__in=["P", "I"]))
                | (Q(created_by__isnull=True) & Q(status__in=["P", "I"]))
            )

        if not self.request.user.is_staff:
            raise PermissionDenied(
                detail="This role is not allowed to access test overview."
            )

        # Admin: no additional filtering (sees every status).
        return queryset

    def _annotate_submitted(self, queryset):
        """
        Annotate `submitted` (distinct students who submitted) when needed:
        1. submitted=true (to display value without a duplicate query), or
        2. ordering references 'submitted' (to enable ordering).
        """
        submitted_param = self.request.query_params.get("submitted", "").lower()
        ordering_param = self.request.query_params.get("ordering", "")
        if submitted_param != "true" and "submitted" not in ordering_param:
            return queryset

        return queryset.annotate(
            submitted=Case(
                When(
                    type="P",
                    then=Count(
                        "productive_test__histories__student",
                        filter=Q(productive_test__histories__type="S"),
                        distinct=True,
                    ),
                ),
                When(
                    type="R",
                    then=Count(
                        "receptive_test__histories__student",
                        filter=Q(receptive_test__histories__type="S"),
                        distinct=True,
                    ),
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    def _annotate_post_count(self, queryset):
        """Annotate `post_count` (forum posts per test) only when requested."""
        post_count_param = self.request.query_params.get("post_count", "").lower()
        if post_count_param != "true":
            return queryset

        return queryset.annotate(
            post_count=Case(
                When(
                    type="P",
                    then=Count(
                        "productive_test__histories__posts",
                        distinct=True,
                    ),
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    def get_serializer_context(self):
        """
        Override to add progress_status/submitted/post_count request flags to context
        """
        context = super().get_serializer_context()

        # Check if progress_status parameter is requested
        progress_status_param = self.request.query_params.get(
            "progress_status", ""
        ).lower()
        request_progress = progress_status_param == "true"
        context["request_progress_status"] = request_progress

        # If progress_status is requested and user is authenticated, check if user is student
        if request_progress and self.request.user.is_authenticated:
            try:
                student = Student.objects.get(user=self.request.user)
                context["student"] = student
            except Student.DoesNotExist:
                context["student"] = None
        else:
            context["student"] = None

        # Check if submitted parameter is requested
        submitted_param = self.request.query_params.get("submitted", "").lower()
        request_submitted = submitted_param == "true"
        context["request_submitted"] = request_submitted

        # Check if post_count parameter is requested
        post_count_param = self.request.query_params.get("post_count", "").lower()
        request_post_count = post_count_param == "true"
        context["request_post_count"] = request_post_count

        return context

    @extend_schema(
        summary="Danh sách bài kiểm tra (tổng quan)",
        description=(
            "Lấy danh sách tất cả bài kiểm tra (tổng quan) với hỗ trợ lọc, sắp xếp và phân trang.\n\n"
            "**Lưu ý về quyền truy cập:**\n"
            "- User thường (không phải admin): Không thấy bài kiểm tra có trạng thái 'R' (Removed). Không được phép filter theo status='R'.\n"
            "- Admin: Thấy tất cả bài kiểm tra, bao gồm 'R'. Được phép filter theo status='R'.\n\n"
            "**Tham số lọc (Query Parameters):**\n"
            "- `type`: Loại bài kiểm tra - R (Receptive: Reading/Listening), P (Productive: Speaking/Writing)\n"
            "- `level`: Cấp độ (A1, A2, B1, B2) - **Hỗ trợ lọc theo nhiều cấp độ**, VD: ?level=A1&level=A2\n"
            "- `skill`: Kỹ năng - R (Reading), L (Listening), S (Speaking), W (Writing)\n"
            "- `status`: Trạng thái - D (Draft), I (In Review), P (Published), R (Removed)\n"
            "- `year`: Lọc theo năm tạo (VD: 2024, 2025, 2026)\n"
            "- `teacher_name`: Lọc theo tên giáo viên (tìm kiếm không phân biệt hoa thường)\n"
            "- `title`: Lọc theo tên bài kiểm tra (tìm kiếm không phân biệt hoa thường)\n"
            "- `mine`: Lọc bài kiểm tra theo giáo viên hiện tại - **Yêu cầu đăng nhập và là giáo viên**\n"
            "  - `true`: Lấy các bài test của chính mình\n"
            "  - `false`: Lấy các bài test không phải của mình\n"
            "  - Không truyền: Lấy tất cả bài test\n"
            "- `my_progress`: Lọc theo trạng thái làm bài của student - **Yêu cầu đăng nhập và là student**\n"
            "  - `completed`: Các bài test đã submit và không còn nháp (hoàn thành)\n"
            "  - `draft`: Các bài test đang có nháp (đang làm dở, dù có submit hay chưa)\n"
            "  - `none`: Các bài test chưa làm\n"
            "- `progress_status`: Hiển thị trạng thái hoàn thành của student (true/false) - **Chỉ áp dụng cho student đã đăng nhập**\n"
            "- `submitted`: Hiển thị số lượng học sinh đã submit bài test (true/false)\n"
            "- `post_count`: Hiển thị số lượng bài post trong forum của bài test (true/false)\n"
            "- `my_posts`: Lọc test mà student hiện tại đã có bài post trên forum (true/false) - **Yêu cầu đăng nhập và là student**\n"
            "  - `true`: Các test student đã có ít nhất 1 bài post trên forum\n"
            "  - `false`: Toàn bộ test Productive (tương đương lọc type=P), không lọc theo post\n"
            "- `page`: Số trang (mặc định: 1)\n"
            "- `page_size`: Số phần tử mỗi trang (mặc định: 10, tối đa: 100)\n\n"
            "**Tham số sắp xếp (Ordering):**\n"
            "- `ordering`: Sắp xếp kết quả\n"
            "  - `created_at` - Ngày tạo (cũ nhất trước)\n"
            "  - `-created_at` - Ngày tạo (mới nhất trước) [mặc định]\n"
            "  - `updated_at` - Ngày cập nhật (cũ nhất trước)\n"
            "  - `-updated_at` - Ngày cập nhật (mới nhất trước)\n"
            "  - `title` - Tên (A-Z)\n"
            "  - `-title` - Tên (Z-A)\n"
            "  - `submitted` - Số lượng submit (ít nhất trước)\n"
            "  - `-submitted` - Số lượng submit (nhiều nhất trước)\n\n"
            "**Lưu ý về tham số `mine`:**\n"
            "- Chỉ giáo viên đã đăng nhập mới được sử dụng tham số `mine` (true hoặc false)\n"
            "- `mine=true`: Lấy các bài test do chính giáo viên hiện tại tạo\n"
            "- `mine=false`: Lấy các bài test do giáo viên khác tạo (không phải của mình)\n"
            "- Không truyền `mine`: Lấy tất cả bài test\n"
            "- Nếu chưa đăng nhập → 403 Forbidden\n"
            "- Nếu không phải giáo viên → 403 Forbidden\n\n"
            "**Lưu ý về tham số `my_progress`:**\n"
            "- Chỉ student đã đăng nhập mới được sử dụng tham số này\n"
            "- `my_progress=completed`: Lấy các bài đã submit VÀ không còn nháp (hoàn toàn xong)\n"
            "- `my_progress=draft`: Lấy các bài đang có nháp (ưu tiên draft - dù có submit hay chưa, nếu còn draft thì vẫn đang làm)\n"
            "- `my_progress=none`: Lấy các bài chưa làm (không có lịch sử)\n\n"
            "**Lưu ý về tham số `progress_status`:**\n"
            "- Khi `progress_status=true`, API sẽ trả về thêm trường `progress_status` cho mỗi test\n"
            "- Chỉ áp dụng cho student đã đăng nhập\n"
            "- Giá trị trả về:\n"
            "  - `completed`: Student đã submit bài test (có ít nhất 1 submission)\n"
            "  - `draft`: Student chỉ có bản nháp (draft), chưa submit\n"
            "  - `none`: Student chưa làm bài test này\n"
            "- Nếu không truyền `progress_status=true` hoặc user không phải student, trường `progress_status` sẽ không xuất hiện trong response\n\n"
            "**Lưu ý về tham số `submitted`:**\n"
            "- Khi `submitted=true`, API sẽ trả về thêm trường `submitted` cho mỗi test\n"
            "- Trường `submitted` cho biết tổng số lượng học sinh đã submit bài test đó (type='S')\n"
            "\n"
            "**Lưu ý về tham số `post_count`:**\n"
            "- Khi `post_count=true`, API sẽ trả về thêm trường `post_count` cho mỗi test\n"
            "- Trường `post_count` cho biết tổng số bài post forum của bài test đó\n"
            "- Với Receptive test (type='R'), `post_count` luôn là 0\n"
            "\n"
            "**Lưu ý về tham số `my_posts`:**\n"
            "- Chỉ student đã đăng nhập mới được sử dụng tham số này\n"
            "- `my_posts=true`: Lấy các test mà student đã có ít nhất 1 bài post trên forum của test đó (thực tế chỉ ra test Productive)\n"
            "- `my_posts=false`: Lấy toàn bộ test Productive (tương đương lọc type=P), không lọc theo việc đã post hay chưa\n"
            "- Vì forum post chỉ tồn tại cho Productive test nên cả hai giá trị chỉ trả về test Productive\n"
            "- Nếu chưa đăng nhập hoặc không phải student → 403 Forbidden\n"
            "**Ví dụ:**\n"
            "- `/api/tests/?type=R` - Lấy tất cả bài Receptive Test (Reading/Listening)\n"
            "- `/api/tests/?type=P&level=B1` - Lấy bài Productive Test cấp B1\n"
            "- `/api/tests/?level=B1&skill=R` - Lấy bài Reading cấp B1\n"
            "- `/api/tests/?status=P&page=2&page_size=20` - Trang 2, 20 bài/trang, chỉ Published\n"
            "- `/api/tests/?year=2026` - Lấy tất cả bài test được tạo năm 2026\n"
            "- `/api/tests/?teacher_name=Nguyen` - Lấy bài test của giáo viên có tên chứa 'Nguyen'\n"
            "- `/api/tests/?ordering=title` - Sắp xếp theo tên A-Z\n"
            "- `/api/tests/?ordering=-created_at&skill=R` - Bài Reading, mới nhất trước\n"
            "- `/api/tests/?mine=true` - Lấy tất cả bài kiểm tra của giáo viên hiện tại\n"
            "- `/api/tests/?mine=false` - Lấy tất cả bài kiểm tra của giáo viên khác (không phải của mình)\n"
            "- `/api/tests/?mine=true&status=D` - Lấy bài Draft của giáo viên hiện tại\n"
            "- `/api/tests/?my_progress=completed` - (Student) Lấy các bài test đã hoàn thành (có submission, không còn draft)\n"
            "- `/api/tests/?my_progress=draft` - (Student) Lấy các bài test đang có nháp (đang làm dở, ưu tiên draft)\n"
            "- `/api/tests/?my_progress=none` - (Student) Lấy các bài test chưa làm\n"
            "- `/api/tests/?my_progress=completed&level=B1` - (Student) Bài test B1 đã hoàn thành\n"
            "- `/api/tests/?year=2026&teacher_name=Vu` - Lấy bài test năm 2026 của giáo viên tên 'Vu'\n"
            "- `/api/tests/?progress_status=true` - Lấy danh sách bài test kèm trạng thái hoàn thành của student\n"
            "- `/api/tests/?progress_status=true&level=B1` - Lấy bài test cấp B1 kèm trạng thái hoàn thành\n"
            "- `/api/tests/?submitted=true` - Lấy danh sách bài test kèm số lượng submission\n"
            "- `/api/tests/?submitted=true&ordering=-submitted` - Lấy bài test kèm số submission, sắp xếp theo nhiều nhất\n"
            "- `/api/tests/?ordering=-submitted` - Sắp xếp theo nhiều submission (KHÔNG hiển thị field submitted)\n"
            "- `/api/tests/?mine=true&submitted=true&ordering=-submitted` - Bài test của mình, xem bài nào được submit nhiều nhất\n"
            "- `/api/tests/?post_count=true` - Lấy danh sách bài test kèm số lượng bài post forum\n"
            "- `/api/tests/?my_posts=true` - (Student) Lấy các test mà mình đã có bài post trên forum\n"
            "- `/api/tests/?my_posts=false` - (Student) Lấy toàn bộ test Productive (tương đương type=P)"
        ),
        tags=["tests (overview)"],
        parameters=[
            OpenApiParameter(
                name="type",
                description="Loại bài kiểm tra (R: Receptive - Reading/Listening, P: Productive - Speaking/Writing)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="level",
                description="Cấp độ (A1, A2, B1, B2) - Hỗ trợ lọc theo nhiều cấp độ, VD: ?level=A1&level=A2",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="skill",
                description="Kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status",
                description="Trạng thái (D: Draft, I: In Review, P: Published, R: Removed)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="year",
                description="Lọc theo năm tạo (VD: 2024, 2025, 2026)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="teacher_name",
                description="Lọc theo tên giáo viên (tìm kiếm không phân biệt hoa thường, có thể tìm một phần tên)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="title",
                description="Lọc theo tên bài kiểm tra (tìm kiếm không phân biệt hoa thường)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="mine",
                description=(
                    "Lọc bài kiểm tra theo giáo viên hiện tại (true/false). "
                    "true: Lấy bài test của mình, false: Lấy bài test không phải của mình, không truyền: Lấy tất cả. "
                    "Yêu cầu: Phải đăng nhập và là giáo viên. "
                    "Nếu không thỏa điều kiện sẽ trả về 403."
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="my_progress",
                description=(
                    "Lọc theo trạng thái làm bài của student (completed/draft/none). "
                    "completed: Đã submit và không còn nháp, draft: Đang có nháp (ưu tiên), none: Chưa làm. "
                    "Yêu cầu: Phải đăng nhập và là student. "
                ),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="progress_status",
                description=(
                    "Hiển thị trạng thái hoàn thành của student (true/false). "
                    "Chỉ áp dụng cho student đã đăng nhập. "
                    "Trả về: completed (đã submit), draft (chỉ có nháp), none (chưa làm). "
                    "Nếu không truyền tham số này hoặc user không phải student, trường progress_status sẽ không xuất hiện trong response."
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="submitted",
                description=(
                    "Hiển thị số lượng học sinh đã submit bài test (true/false). "
                    "Khi submitted=true, API sẽ trả về thêm trường 'submitted' cho mỗi test, "
                    "cho biết tổng số lượng submission (type='S') của bài test đó. "
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="post_count",
                description=(
                    "Hiển thị số lượng bài post forum của bài test (true/false). "
                    "Khi post_count=true, API sẽ trả về thêm trường 'post_count' cho mỗi test. "
                    "Với Receptive test (type='R'), giá trị luôn là 0. "
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="my_posts",
                description=(
                    "Lọc test mà student hiện tại đã có bài post trên forum (true/false). "
                    "true: Các test student đã có bài post; "
                    "false: Toàn bộ test Productive (tương đương type=P), không lọc theo post. "
                    "Yêu cầu: Phải đăng nhập và là student. "
                    "Nếu không thỏa điều kiện sẽ trả về 403."
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="page",
                description="Số trang (mặc định: 1)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                description="Số phần tử mỗi trang (mặc định: 10, tối đa: 100)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="ordering",
                description=(
                    "Sắp xếp kết quả: created_at, -created_at, updated_at, -updated_at, title, -title, submitted, -submitted. "
                ),
                required=False,
                type=str,
            ),
        ],
        responses={
            200: TestSerializer(many=True),
            403: OpenApiResponse(
                description="Forbidden - Using mine parameter but not a teacher, or using my_progress parameter but not a student, or not authenticated",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "string",
                            "example": "Only teachers can use 'mine' parameter to filter tests.",
                        },
                    },
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        # Filter is handled by DjangoFilterBackend + TestFilter
        # Pagination is handled by TestPagination
        # 'mine' filter is handled in get_queryset()
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo bài kiểm tra mới (thông tin tổng quan)",
        description=(
            "Tạo một bài kiểm tra mới (chỉ giáo viên).\n\n"
            "**Quyền truy cập:**\n"
            "- **Bắt buộc**: Người dùng phải là giáo viên\n"
            "- Nếu user không phải teacher → 403 Forbidden\n\n"
            "**Trạng thái mặc định:**\n"
            "- Bài kiểm tra được tạo với trạng thái mặc định là `D` (Draft)\n"
            "- `created_by` tự động được set là teacher của người dùng\n\n"
            "**Tham số bắt buộc:**\n"
            "- `title`: Tên bài kiểm tra (không quá 255 ký tự, không được để trống)\n"
            "- `type`: Loại bài kiểm tra - phải là một trong [R, P]:\n"
            "  - R: Receptive (dành cho Reading/Listening)\n"
            "  - P: Productive (dành cho Speaking/Writing)\n"
            "- `level`: Cấp độ - phải là một trong [A1, A2, B1, B2]\n"
            "- `skill`: Kỹ năng - phải là một trong [R, L, S, W]:\n"
            "  - R: Reading (Đọc) - yêu cầu type=R\n"
            "  - L: Listening (Nghe) - yêu cầu type=R\n"
            "  - S: Speaking (Nói) - yêu cầu type=P\n"
            "  - W: Writing (Viết) - yêu cầu type=P\n"
            "- `time`: Thời gian làm bài (phút, tối thiểu 1)\n"
            "- `description`: Mô tả bài kiểm tra (không được để trống)\n\n"
            "**Tham số tùy chọn:**\n"
            "- `status`: Trạng thái - D (Draft), I (In Review), P (Published) (mặc định: D)\n\n"
            "**Lưu ý:**\n"
            "- `type` và `skill` phải tương thích:\n"
            "  - type=R chỉ dùng với skill=R hoặc skill=L\n"
            "  - type=P chỉ dùng với skill=S hoặc skill=W"
        ),
        tags=["tests (overview)"],
        request=inline_serializer(
            name="TestCreateRequest",
            fields={
                "title": serializers.CharField(
                    required=True, help_text="Tên bài kiểm tra"
                ),
                "type": serializers.ChoiceField(
                    choices=["R", "P"],
                    required=True,
                    help_text="Loại bài kiểm tra (R: Receptive - Reading/Listening, P: Productive - Speaking/Writing)",
                ),
                "level": serializers.ChoiceField(
                    choices=["A1", "A2", "B1", "B2"],
                    required=True,
                    help_text="Cấp độ (A1, A2, B1, B2)",
                ),
                "skill": serializers.ChoiceField(
                    choices=["R", "L", "S", "W"],
                    required=True,
                    help_text="Kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)",
                ),
                "time": serializers.IntegerField(
                    required=True, help_text="Thời gian làm bài (phút, tối thiểu 1)"
                ),
                "description": serializers.CharField(
                    required=True, help_text="Mô tả bài kiểm tra"
                ),
                "status": serializers.ChoiceField(
                    choices=["D", "I", "P"],
                    required=False,
                    default="D",
                    help_text=(
                        "Trạng thái (D: Draft, I: In Review, P: Published). "
                        "Nếu không gửi sẽ mặc định là D."
                    ),
                ),
            },
        ),
        responses={
            201: OpenApiResponse(
                description="Test created successfully",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "title": {"type": "string", "example": "IELTS Reading Test 1"},
                        "type": {
                            "type": "string",
                            "enum": ["R", "P"],
                            "example": "R",
                            "description": "R: Receptive, P: Productive",
                        },
                        "level": {
                            "type": "string",
                            "enum": ["A1", "A2", "B1", "B2"],
                            "example": "B1",
                        },
                        "skill": {
                            "type": "string",
                            "enum": ["R", "L", "S", "W"],
                            "example": "R",
                        },
                        "time": {"type": "integer", "example": 60},
                        "description": {
                            "type": "string",
                            "example": "Test description...",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["D", "I", "P"],
                            "example": "D",
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "created_by": {"type": "integer", "example": 1},
                    },
                    "required": [
                        "id",
                        "title",
                        "type",
                        "level",
                        "skill",
                        "time",
                        "description",
                        "status",
                        "created_at",
                        "updated_at",
                    ],
                },
            ),
            400: OpenApiResponse(
                description="Validation error",
                response={
                    "type": "object",
                    "example": {
                        "title": ["This field is required."],
                        "level": ["Must be one of: B1, B2, A1, A2."],
                    },
                },
            ),
            401: OpenApiResponse(
                description="Unauthorized - User not authenticated",
            ),
            403: OpenApiResponse(
                description="Forbidden - User is not a teacher",
                response={
                    "type": "object",
                    "example": {"detail": "Only teachers can perform this action."},
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
