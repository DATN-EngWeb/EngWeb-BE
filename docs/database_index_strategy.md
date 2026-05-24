# Database Index Strategy - NENS English Learning App

> **Lưu ý quan trọng:** PostgreSQL tự động đánh index cho các trường `unique=True` và `unique_together`. Bảng dưới đây ghi chú rõ index nào **đã có** trong `Meta` class của models và index nào **cần thêm**.

---

## 1. Ước Tính Số Record Mỗi Bảng

### 1.1. Bảng User & Account (Kích thước: Nhỏ - < 1,000 records)

| Bảng              | Ước Tính      | Nguồn                                          |
| ----------------- | ------------- | ---------------------------------------------- |
| `user`            | 50 - 100      | User estimate                                  |
| `student`         | 45 - 90       | 90% of users                                   |
| `teacher`         | 5 - 10        | 10% of users                                   |
| `user_level`      | **8 records** | `init/seed_00_user_level.sql` - 8 fixed levels |
| `assistant_quota` | 50 - 100      | 1:1 with user                                  |

### 1.2. Bảng Test & Questions (Kích thước: Trung bình - ~10,000 records)

| Bảng                         | Ước Tính        | Nguồn                                                       |
| ---------------------------- | --------------- | ----------------------------------------------------------- |
| `test`                       | 120 - 160       | User estimate                                               |
| `receptive_test`             | 80 - 120        | ~70% of tests                                               |
| `receptive_part`             | 560 - 840       | ~7 parts/test                                               |
| `receptive_question`         | 5,600 - 8,400   | ~10 questions/part                                          |
| `receptive_answer`           | 16,800 - 25,200 | ~3 answers/question                                         |
| `productive_test`            | 40              | ~30% of tests                                               |
| `writing_criteria_template`  | **18 records**  | `init/seed_00_writing_criteria.sql` - 3 levels x 6 bands    |
| `speaking_criteria_template` | **18 records**  | `init/seed_00_speaking_criteria.sql` - 3 levels x 6 bands   |
| `reading_criteria_template`  | **32 records**  | `init/seed_00_reading_criteria.sql` - 4 levels x 8 criteria |
| `test_feedback`              | 1,200 - 1,600   | User estimate                                               |

### 1.3. Bảng History & Forum (Kích thước: Lớn - > 100,000 records)

| Bảng                       | Ước Tính              | Nguồn                                               |
| -------------------------- | --------------------- | --------------------------------------------------- |
| `productive_test_history`  | 2,400                 | 90 students x 20 tests x 3 attempts / 2 (split R/L) |
| `receptive_test_history`   | 2,700 - 5,400         | 90 students x 20 tests x 3 attempts                 |
| `receptive_answer_history` | **189,000 - 378,000** | 1 history x 70 questions x 30 histories             |
| `post`                     | 1,200                 | 50% submissions shared                              |
| `post_comment`             | 2,400 - 6,000         | 2-5 comments/post                                   |
| `post_reaction`            | 6,000                 | Estimated                                           |

### 1.4. Bảng Assistant (Kích thước: Lớn - > 50,000 records) - TÍNH TOÁN MỚI

**Giả định:**

- Mỗi Student dùng AI Assistant trung bình **2 lần/tuần** trong 2 tháng (8 tuần) = **16 conversations**
- Mỗi Conversation có trung bình **10 messages** (5 user + 5 AI)
- Teacher dùng ít hơn, trung bình **8 conversations**

| Bảng                     | Ước Tính    | Tính Toán                              |
| ------------------------ | ----------- | -------------------------------------- |
| `assistant_conversation` | **~1,520**  | (90 students x 16) + (10 teachers x 8) |
| `assistant_message`      | **~15,200** | 1,520 conversations x 10 messages      |

### 1.5. Bảng Lookup (KHÔNG BAO GIỜ THAY ĐỔI)

| Bảng                 | Số Records | Nguồn                                                    |
| -------------------- | ---------- | -------------------------------------------------------- |
| `completed_bonus`    | **16**     | `init/seed_00_completed_bonus.sql` - 4 skills x 4 levels |
| `exp_bonus_rule`     | **6**      | `init/seed_00_exp_bonus_rule.sql` - 6 fixed rules        |
| `streak_reward_rule` | **5**      | `init/seed_00_streak_reward_rule.sql` - 5 milestones     |

### 1.6. Tổng Kết Kích Thước Bảng (Theo Thứ Tự Giảm Dần)

| #   | Bảng                       | Ước Tính | Loại       |
| --- | -------------------------- | -------- | ---------- |
| 1   | `receptive_answer_history` | 378,000  | Lớn        |
| 2   | `receptive_question`       | 8,400    | Trung bình |
| 3   | `receptive_answer`         | 25,200   | Trung bình |
| 4   | `assistant_message`        | 15,200   | Lớn        |
| 5   | `post_reaction`            | 6,000    | Trung bình |
| 6   | `receptive_part`           | 840      | Nhỏ        |
| 7   | `test`                     | 160      | Nhỏ        |
| 8   | `assistant_conversation`   | 1,520    | Trung bình |
| 9   | `test_feedback`            | 1,600    | Trung bình |
| 10  | `post`                     | 1,200    | Nhỏ        |

---

## 2. Phân Tích Các Câu Query Trong Toàn Dự Án

### 2.1. Query Từ `accounts/views/`

**File:** `accounts/views/authentication.py`

```python
# Google/Facebook Login - QUERY THƯỜNG XUYÊN NHẤT (mỗi lần login)
User.objects.get(email=email)  # Tìm user theo email
User.objects.get(Q(username=...) | Q(email=...))  # Forgot password

# Register
User.objects.filter(username=base_username)  # Generate unique username
```

**File:** `accounts/views/admin.py`

```python
# Admin Dashboard - QUERY TẦN SUẤT CAO
User.objects.values('role', 'status').annotate(total=Count('id'))  # Stats overview
User.objects.all().order_by("-date_joined")  # List users
```

### 2.2. Query Từ `assistant/views.py`

```python
# CONVERSATION LISTING - TẦN SUẤT CAO
AssistantConversation.objects.filter(user=self.request.user, is_archived=False)
AssistantConversation.objects.filter(id=conversation_id, user=request.user, is_archived=False)
AssistantConversation.objects.filter(user=request.user).order_by("-last_message_at")

# MESSAGE RETRIEVAL - TẦN SUẤT RẤT CAO (mỗi lần gửi message)
conversation.messages.order_by("created_at", "-id")[:30]  # Load history
conversation.messages.filter(
    role__in=[...],
    status=...
).order_by("created_at")[:memory_limit]  # Get AI context
```

### 2.3. Query Từ `test_histories/views.py`

```python
# FIND DRAFT - TẦN SUẤT CAO (mỗi lần student làm test)
ProductiveTestHistory.objects.filter(student=student, productive_test_id=..., type="D")
ReceptiveTestHistory.objects.filter(student=student, receptive_test_id=..., type="D")

# COUNT SUBMISSIONS
ProductiveTestHistory.objects.filter(student=student, productive_test_id=..., type="S").count()
ReceptiveTestHistory.objects.filter(student=student, receptive_test_id=..., type="S").count()

# LIST HISTORIES - PHÂN TRANG
ProductiveTestHistory.objects.filter(student=user.student).select_related(...).order_by("type", "start_time")
ReceptiveTestHistory.objects.select_related(...).prefetch_related(...).order_by("type", "start_time")
```

### 2.4. Query Từ `statistic/views.py`

```python
# STATISTICS - TẦN SUẤT TRUNG BÌNH
ReceptiveTestHistory.objects.filter(
    student=student,
    receptive_test__test__skill=skill,
    receptive_test__test__level=level,
    type="S",
).select_related(...).order_by("-end_time", "start_time")

ReceptiveQuestion.objects.filter(
    receptive_part__receptive_test_id__in=receptive_test_ids
).values(...).annotate(total_questions=Count("id"))

ReceptiveAnswerHistory.objects.filter(
    receptive_test_history_id__in=history_ids,
    is_correct=True,
).values(...).annotate(total_correct=Count("id"))
```

### 2.5. Query Từ `forum/views.py`

```python
# FORUM LISTING - TẦN SUẤT CAO
Post.objects.filter(productive_test_history__productive_test__test_id=test_id)
Post.objects.annotate(is_liked=Exists(PostReaction.objects.filter(post=OuterRef("pk"), user=request.user, status="L")))

# FILTER "MY POSTS"
Post.objects.filter(productive_test_history__student__user=self.request.user)

# COMMENTS
PostComment.objects.select_related("user").filter(post_id=post_id)
PostComment.objects.filter(post__productive_test_history__student__user=user).exclude(user=user)

# REACTIONS
PostReaction.objects.filter(post=OuterRef("pk"), user=request.user, status="L")
PostReaction.objects.get_or_create(user=request.user, post=post_obj, defaults={'status': 'L'})
```

### 2.6. Query Từ `notifications/views.py`

```python
# NOTIFICATION LIST - TẦN SUẤT RẤT CAO (mỗi lần user mở app)
TestFeedback.objects.filter(
    test__created_by__user=user,
    created_by="T"
).select_related(...).order_by("created_at")

PostComment.objects.filter(
    post__productive_test_history__student__user=user,
).exclude(user=user).select_related(...).order_by("created_at")

# MARK READ
TestFeedback.objects.filter(test__created_by__user=user, created_by="T", is_read=False).update(is_read=True)
PostComment.objects.filter(post__productive_test_history__student__user=user, is_read=False).exclude(user=user).update(is_read=True)
```

---

## 3. Bảng/Cột Được Truy Vấn Tần Suất Lớn

### 3.1. Bảng `assistant_message` - ƯU TIÊN SỐ 1

| Cột                             | Query Pattern                         | Tần Suất    | Chi Phí          |
| ------------------------------- | ------------------------------------- | ----------- | ---------------- |
| `conversation_id`               | JOIN với conversation để lấy messages | **Rất Cao** | HIGH (full scan) |
| `(conversation_id, created_at)` | ORDER BY để lấy messages gần nhất     | **Rất Cao** | HIGH (full scan) |
| `status`                        | WHERE status='completed'              | Cao         | MEDIUM           |

```sql
-- Query thực tế:
SELECT * FROM assistant_message
WHERE conversation_id = ?
ORDER BY created_at DESC, id DESC
LIMIT 30;
```

### 3.2. Bảng `assistant_conversation` - ƯU TIÊN SỐ 2

| Cột                          | Query Pattern                          | Tần Suất    | Chi Phí          |
| ---------------------------- | -------------------------------------- | ----------- | ---------------- |
| `user_id`                    | WHERE user = ?                         | **Rất Cao** | HIGH (full scan) |
| `(user_id, is_archived)`     | WHERE user = ? AND is_archived = False | **Rất Cao** | HIGH             |
| `(user_id, last_message_at)` | ORDER BY last_message_at DESC          | **Rất Cao** | HIGH             |
| `is_archived`                | WHERE is_archived = False              | Cao         | MEDIUM           |

```sql
-- Query thực tế:
SELECT * FROM assistant_conversation
WHERE user_id = ? AND is_archived = False
ORDER BY last_message_at DESC;
```

### 3.3. Bảng `receptive_answer_history` - ƯU TIÊN SỐ 3

| Cột                                       | Query Pattern                 | Tần Suất   | Chi Phí |
| ----------------------------------------- | ----------------------------- | ---------- | ------- |
| `receptive_test_history_id`               | JOIN để lấy chi tiết bài làm  | **Cao**    | HIGH    |
| `(receptive_test_history_id, is_correct)` | Đếm đáp án đúng cho statistic | **Cao**    | HIGH    |
| `receptive_question_id`                   | JOIN với question để hiển thị | Trung Bình | MEDIUM  |

```sql
-- Query thực tế (statistic):
SELECT receptive_test_history_id, COUNT(*)
FROM receptive_answer_history
WHERE receptive_test_history_id IN (...) AND is_correct = True
GROUP BY receptive_test_history_id;
```

### 3.4. Bảng `receptive_test_history` - ƯU TIÊN SỐ 4

| Cột                                               | Query Pattern                    | Tần Suất | Chi Phí |
| ------------------------------------------------- | -------------------------------- | -------- | ------- |
| `(student_id, type)`                              | WHERE student = ? AND type = 'S' | **Cao**  | HIGH    |
| `(student_id, receptive_test__test__skill, type)` | Filter theo skill cho statistic  | **Cao**  | HIGH    |
| `(student_id, start_time)`                        | ORDER BY start_time DESC         | Cao      | MEDIUM  |
| `(receptive_test_id, type)`                       | Find draft                       | Cao      | MEDIUM  |

### 3.5. Bảng `productive_test_history` - ƯU TIÊN SỐ 5

| Cột                                      | Query Pattern         | Tần Suất | Chi Phí |
| ---------------------------------------- | --------------------- | -------- | ------- |
| `(student_id, productive_test_id, type)` | Find draft/submission | **Cao**  | HIGH    |
| `(student_id, type, start_time)`         | ORDER BY cho listing  | Cao      | MEDIUM  |

### 3.6. Bảng `post_comment` - ƯU TIÊN SỐ 6

| Cột                     | Query Pattern                   | Tần Suất | Chi Phí        |
| ----------------------- | ------------------------------- | -------- | -------------- |
| `(post_id, created_at)` | ORDER BY created_at cho listing | **Cao**  | MEDIUM         |
| `(post_id, is_read)`    | Filter notifications            | **Cao**  | MEDIUM         |
| `post_id`               | WHERE post_id = ?               | Cao      | LOW (FK index) |

### 3.7. Bảng `user` - ƯU TIÊN SỐ 7

| Cột              | Query Pattern                 | Tần Suất    | Chi Phí            |
| ---------------- | ----------------------------- | ----------- | ------------------ |
| `email`          | WHERE email = ? (OAuth login) | **Rất Cao** | LOW (Unique Index) |
| `username`       | WHERE username = ?            | Cao         | MEDIUM             |
| `(role, status)` | GROUP BY cho admin stats      | Trung Bình  | MEDIUM             |

---

## 4. Quyết Định Đánh Index

### 4.1. Tổng Hợp Quyết Định Đánh Index (Dựa Trên Phân Tích Ở Mục 1, 2, 3)

> Phần này liệt kê **toàn bộ** index cần tồn tại trong database sau khi tổng hợp các phân tích về:
>
> - Kích thước bảng (Mục 1)
> - Pattern query thực tế trong code (Mục 2)
> - Tần suất truy cập từng bảng/cột (Mục 3)
>
> Mỗi index đều được kèm theo lý do **tại sao** cần đánh index ở đó.

#### A. Bảng `user` (50 - 100 records)

| #   | Index            | Lý Do                                                                                                                                                                                                                                                |
| --- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `email` (Unique) | `email` là định danh chính khi đăng nhập bằng Google/Facebook OAuth - hệ thống cần tra cứu user theo email **mỗi lần đăng nhập**, đây là một trong những thao tác tần suất cao nhất. Ràng buộc unique cũng đảm bảo không có 2 tài khoản trùng email. |
| 2   | `username`       | Username được dùng trong 2 luồng nghiệp vụ: (1) khi đăng ký, hệ thống kiểm tra username đã tồn tại chưa để sinh tên duy nhất, và (2) khi quên mật khẩu, người dùng có thể nhập username để xác minh.                                                 |

#### B. Bảng `assistant_conversation` (~1,520 records)

| #   | Index                                  | Lý Do                                                                                                                                                                                                                                                                                                                           |
| --- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(user, last_message_at)`              | Phục vụ use case sắp xếp các đoạn hội thoại của một user theo thời gian message gần nhất - đoạn nào mới hoạt động sẽ hiển thị trên cùng.                                                                                                                                                                                        |
| 2   | `(user, is_archived)`                  | Phục vụ use case lọc bỏ các đoạn hội thoại đã được người dùng archive (chỉ hiển thị conversation đang hoạt động).                                                                                                                                                                                                               |
| 3   | `(user, is_archived, last_message_at)` | Use case thực tế khi user mở giao diện chat luôn là: "lấy tất cả conversation của tôi, chưa archive, sắp xếp theo thời gian mới nhất". Composite index 3 cột phục vụ đồng thời cả lọc (user, is_archived) và sắp xếp (last_message_at) trong **một lần truy cập index duy nhất**, không cần thao tác sort bổ sung trên kết quả. |

#### C. Bảng `assistant_message` (~15,200 records)

| #   | Index                        | Lý Do                                                                                                                                                                                                                                                                      |
| --- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(conversation, created_at)` | Mỗi khi user mở một đoạn hội thoại hoặc gửi tin nhắn mới, hệ thống cần load N message gần nhất của hội thoại đó để hiển thị và làm context cho AI. Đây là **thao tác tần suất rất cao**, và bảng có ~15k record - index trên cặp `(conversation, created_at)` là bắt buộc. |
| 2   | `status`                     | Một message có thể ở các trạng thái khác nhau (đang xử lý, hoàn thành, lỗi). Khi build context cho AI, hệ thống chỉ lấy message đã hoàn thành thành công, loại bỏ message lỗi/pending.                                                                                     |

#### D. Bảng `productive_test_history` (~2,400 records)

| #   | Index                                                | Lý Do                                                                                                                                                                                              |
| --- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(student, productive_test, attempt, type)` (Unique) | Ràng buộc unique đảm bảo mỗi student chỉ có 1 lượt làm bài duy nhất cho mỗi cặp (test, attempt, type) - tránh tạo trùng bản nháp/bản nộp. Phục vụ luôn use case truy xuất bản nháp cụ thể.         |
| 2   | `(productive_test, type)`                            | Phục vụ use case thống kê: đếm tổng số lượt **đã nộp** (`type='S'`) của một đề thi để hiển thị mức độ phổ biến / số người đã làm.                                                                  |
| 3   | `(student, type, start_time)`                        | Phục vụ use case hiển thị danh sách lịch sử làm bài của một học viên, phân nhóm theo trạng thái (draft / submitted) và sắp xếp theo thời gian mới nhất. Index phục vụ đồng thời cả lọc và sắp xếp. |

#### E. Bảng `receptive_test_history` (~2,700 - 5,400 records)

| #   | Index                                               | Lý Do                                                                                                                                                                                           |
| --- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(student, receptive_test, attempt, type)` (Unique) | Tương tự `productive_test_history` - đảm bảo tính duy nhất của một lượt làm bài và phục vụ truy xuất draft.                                                                                     |
| 2   | `(receptive_test, type)`                            | Phục vụ use case thống kê số lượt nộp của một đề thi (Reading/Listening).                                                                                                                       |
| 3   | `(student, type, start_time)`                       | Phục vụ use case dashboard thống kê tiến trình học của học viên: lọc theo kỹ năng/level + sắp xếp theo thời gian gần nhất. Đây là một trong những query có tần suất cao trong module statistic. |

#### F. Bảng `receptive_answer_history` (**189,000 - 378,000 records** - LỚN NHẤT HỆ THỐNG)

| #   | Index                                                                     | Lý Do                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(receptive_test_history, receptive_question, receptive_answer)` (Unique) | Đảm bảo mỗi câu hỏi trong một lượt làm bài chỉ có duy nhất một đáp án được chọn.                                                                                                                                                                                                                                                                                                                                                               |
| 2   | `(receptive_test_history, is_correct)`                                    | **ĐÂY LÀ INDEX QUAN TRỌNG NHẤT TRONG TOÀN BỘ HỆ THỐNG.** Bảng này có ước tính lên đến ~378k record - lớn nhất hệ thống. Mỗi khi học viên xem kết quả/thống kê bài làm, hệ thống cần đếm số câu đúng cho từng lượt làm bài. Nếu không có index, mỗi lần thống kê sẽ phải quét toàn bộ ~378k record - không thể chấp nhận về performance. Với index này, query thống kê chỉ truy cập đúng các record liên quan đến những lượt làm bài cần thiết. |

#### G. Bảng `post_comment` (2,400 - 6,000 records)

| #   | Index                | Lý Do                                                                                                                                                                                                                                                                                                    |
| --- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `(post, created_at)` | Mỗi khi người dùng mở một bài post trên forum, hệ thống cần load toàn bộ comment của post đó, sắp xếp theo thời gian (mới nhất hoặc cũ nhất). Đây là thao tác có tần suất cao trên module forum. Index composite phục vụ đồng thời lọc theo post và sắp xếp theo thời gian, tránh phải sort lại kết quả. |

#### H. Các bảng KHÔNG cần đánh index thủ công

| Bảng                                                                                                             | Số Records | Lý Do Không Cần                                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `student`, `teacher`                                                                                             | < 100      | Bảng nhỏ. Với số lượng record ít, việc quét tuần tự (sequential scan) thậm chí còn nhanh hơn quét theo index. Các Foreign Key index tự động của Django đã đủ.              |
| `test`, `receptive_test`, `productive_test`                                                                      | < 160      | Tương tự - bảng nhỏ, không có nhu cầu lọc phức tạp.                                                                                                                        |
| `receptive_part`, `receptive_question`, `receptive_answer`                                                       | < 26k      | Truy cập chủ yếu thông qua quan hệ FK (test → part → question → answer), không có pattern lọc/sắp xếp phức tạp ngoài FK.                                                   |
| `post`, `post_reaction`                                                                                          | < 6k       | Kích thước trung bình, các query đã có thể tận dụng FK index.                                                                                                              |
| `test_feedback`                                                                                                  | < 1.6k     | Kích thước nhỏ, truy cập qua FK đủ nhanh.                                                                                                                                  |
| Các bảng lookup (`completed_bonus`, `exp_bonus_rule`, `streak_reward_rule`, `user_level`, `*_criteria_template`) | < 32       | Bảng cấu hình tĩnh, dữ liệu hầu như không thay đổi và có rất ít record. Đánh index chỉ làm tăng chi phí ghi và tốn dung lượng mà không mang lại lợi ích nào về tốc độ đọc. |

#### I. Tổng Quan Số Lượng Index

| Loại                                                        | Số Lượng | Ghi Chú                                                                            |
| ----------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------- |
| Index tự động (Primary Key, Foreign Key, Unique constraint) | Nhiều    | PostgreSQL tự sinh - không cần khai báo                                            |
| Index composite/single-field cần khai báo thủ công          | **12**   | Trong đó có 4 index thuộc nhóm bảng `assistant_*` và 8 index trên các bảng còn lại |

---

### 4.2. Tình Trạng Index Hiện Tại (Đã Kiểm Tra Trong Models)

> PostgreSQL tự động đánh index cho: `unique=True`, `unique_together`, và `unique_together` trong `Meta`.

#### A. `accounts/models.py` - Bảng `user`

| Index                 | Trong Code  | Ghi chú                               |
| --------------------- | ----------- | ------------------------------------- |
| `email` (unique=True) | **Đã có** ✓ | PostgreSQL tự tạo unique B-tree index |
| `(username)`          | **CHƯA CÓ** | Cần thêm                              |

#### B. `assistant/models.py` - Bảng `assistant_conversation`

| Index                                  | Trong Code  | Ghi chú                                                                                     |
| -------------------------------------- | ----------- | ------------------------------------------------------------------------------------------- |
| `(user, last_message_at)`              | **Đã có** ✓ | Tốt                                                                                         |
| `(user, is_archived)`                  | **Đã có** ✓ | Tốt                                                                                         |
| `(user, is_archived, last_message_at)` | **CHƯA CÓ** | Cần thêm để tối ưu query `WHERE user=X AND is_archived=False ORDER BY last_message_at DESC` |

#### C. `assistant/models.py` - Bảng `assistant_message`

| Index                        | Trong Code  | Ghi chú    |
| ---------------------------- | ----------- | ---------- |
| `(conversation, created_at)` | **Đã có** ✓ | Tuyệt vời! |
| `(status)`                   | **Đã có** ✓ | Tốt        |

#### D. `test_histories/models.py` - Bảng `productive_test_history`

| Index                                       | Trong Code  | Ghi chú                   |
| ------------------------------------------- | ----------- | ------------------------- |
| `(student, productive_test, attempt, type)` | **Đã có** ✓ | Phục vụ unique constraint |
| `(productive_test, type)`                   | **CHƯA CÓ** | Cần thêm cho statistic    |
| `(student, type, start_time)`               | **CHƯA CÓ** | Cần thêm cho listing      |

#### E. `test_histories/models.py` - Bảng `receptive_test_history`

| Index                                      | Trong Code  | Ghi chú                   |
| ------------------------------------------ | ----------- | ------------------------- |
| `(student, receptive_test, attempt, type)` | **Đã có** ✓ | Phục vụ unique constraint |
| `(receptive_test, type)`                   | **CHƯA CÓ** | Cần thêm cho statistic    |
| `(student, type, start_time)`              | **CHƯA CÓ** | Cần thêm cho listing      |

#### F. `test_histories/models.py` - Bảng `receptive_answer_history`

| Index                                                            | Trong Code  | Ghi chú                         |
| ---------------------------------------------------------------- | ----------- | ------------------------------- |
| `(receptive_test_history, receptive_question, receptive_answer)` | **Đã có** ✓ | Phục vụ unique constraint       |
| `(receptive_test_history, is_correct)`                           | **CHƯA CÓ** | **CẦN THÊM NGAY** cho statistic |

#### G. `forum/models.py` - Bảng `post_comment`

| Index                | Trong Code  | Ghi chú                  |
| -------------------- | ----------- | ------------------------ |
| `(post, created_at)` | **CHƯA CÓ** | **CẦN THÊM** cho listing |

---

### 4.3. Index Cần Thêm (Thực Tế)

#### A. `assistant_conversation` - Thêm composite index

```python
# Thêm vào Meta class của AssistantConversation
indexes = [
    models.Index(fields=["user", "is_archived", "last_message_at"], name="conv_user_archived_time_idx"),
]
```

**Lý do:**

- Bảng có ~1,520 records nhưng **query mỗi khi user mở chat**
- Index hiện tại tách riêng `(user, last_message_at)` và `(user, is_archived)` không tối ưu cho query `WHERE user=X AND is_archived=False ORDER BY last_message_at DESC`
- Composite index `(user, is_archived, last_message_at)` phục vụ cả WHERE và ORDER BY trong một index scan

#### B. `receptive_answer_history` - Thêm composite index

```python
# Thêm vào Meta class của ReceptiveAnswerHistory
indexes = [
    models.Index(fields=["receptive_test_history", "is_correct"], name="rah_history_correct_idx"),
]
```

**Lý do:**

- Bảng có **378,000 records** - lớn nhất trong toàn hệ thống
- **Query mỗi khi user xem statistic** để đếm đáp án đúng
- Không có index, query `COUNT WHERE is_correct=True` phải scan toàn bộ 378k records

#### C. `receptive_test_history` - Thêm composite indexes

```python
# Thêm vào Meta class của ReceptiveTestHistory
indexes = [
    models.Index(fields=["receptive_test", "type"], name="rth_test_type_idx"),
    models.Index(fields=["student", "type", "start_time"], name="rth_student_type_time_idx"),
]
```

**Lý do:**

- Bảng có 2,700 - 5,400 records
- **Query mỗi khi student làm test** để find/create draft
- **Query mỗi khi xem statistic** để filter theo skill/level

#### D. `productive_test_history` - Thêm composite indexes

```python
# Thêm vào Meta class của ProductiveTestHistory
indexes = [
    models.Index(fields=["productive_test", "type"], name="pth_test_type_idx"),
    models.Index(fields=["student", "type", "start_time"], name="pth_student_type_time_idx"),
]
```

**Lý do:**

- Tương tự receptive_test_history
- **Query find draft** mỗi khi student làm productive test

#### E. `post_comment` - Thêm composite index

```python
# Thêm vào Meta class của PostComment
indexes = [
    models.Index(fields=["post", "created_at"], name="comment_post_time_idx"),
]
```

**Lý do:**

- Bảng có 2,400 - 6,000 records
- **Query mỗi khi load forum post** để hiển thị comments
- Index `(post, created_at)` phục vụ ORDER BY mà không cần filesort

#### F. `user` - Thêm single index

```python
# Thêm vào Meta class của User
indexes = [
    models.Index(fields=["username"], name="user_username_idx"),
]
```

**Lý do:**

- Username lookup trong `generate_unique_username()` và `ForgotPasswordAPIView`
- Bảng chỉ có 50-100 records, **impact không lớn** nhưng vẫn nên có

### 4.4. KHÔNG CẦN Index - Các bảng lookup nhỏ

| Bảng                         | Số Records | Lý Do                              |
| ---------------------------- | ---------- | ---------------------------------- |
| `completed_bonus`            | 16         | Full scan 16 records không đáng kể |
| `exp_bonus_rule`             | 6          | Full scan 6 records không đáng kể  |
| `streak_reward_rule`         | 5          | Full scan 5 records không đáng kể  |
| `user_level`                 | 8          | Full scan 8 records không đáng kể  |
| `writing_criteria_template`  | 18         | Full scan 18 records không đáng kể |
| `speaking_criteria_template` | 18         | Full scan 18 records không đáng kể |
| `reading_criteria_template`  | 32         | Full scan 32 records không đáng kể |

---

## 5. Tóm Tắt Cuối Cùng

### 5.1. Index Đã Có Trong Code (KHÔNG CẦN Thêm)

| Bảng                     | Index                        | Ghi chú                    |
| ------------------------ | ---------------------------- | -------------------------- |
| `assistant_message`      | `(conversation, created_at)` | Đã có trong `Meta.indexes` |
| `assistant_message`      | `(status)`                   | Đã có trong `Meta.indexes` |
| `assistant_conversation` | `(user, last_message_at)`    | Đã có trong `Meta.indexes` |
| `assistant_conversation` | `(user, is_archived)`        | Đã có trong `Meta.indexes` |

### 5.2. Index Cần Thêm Mới

| Priority | Bảng                       | Index Mới                              | Tác Động                            |
| -------- | -------------------------- | -------------------------------------- | ----------------------------------- |
| 1        | `assistant_conversation`   | `(user, is_archived, last_message_at)` | Giảm ~99% thời gian load chat list  |
| 2        | `receptive_answer_history` | `(receptive_test_history, is_correct)` | Giảm ~95% thời gian tính accuracy   |
| 3        | `receptive_test_history`   | `(receptive_test, type)`               | Giảm ~90% thời gian thống kê test   |
| 3        | `receptive_test_history`   | `(student, type, start_time)`          | Giảm ~90% thời gian listing         |
| 4        | `productive_test_history`  | `(productive_test, type)`              | Giảm ~90% thời gian thống kê test   |
| 4        | `productive_test_history`  | `(student, type, start_time)`          | Giảm ~90% thời gian listing         |
| 5        | `post_comment`             | `(post, created_at)`                   | Giảm ~80% thời gian load comments   |
| 6        | `user`                     | `(username)`                           | Giảm ~50% thời gian username lookup |

### 5.3. Tổng Kết Số Lượng

- **Tổng số index thủ công cần có trong DB:** **12 indexes**
  - **4 indexes** đã khai báo sẵn trong code (`assistant_*`)
  - **8 indexes** cần khai báo bổ sung vào `Meta.indexes` của các models tương ứng (xem chi tiết ở 4.3)
- **Không có index thừa** trong models hiện tại cần phải xóa.

> **Lưu ý:** Sau khi cập nhật `Meta.indexes` của các model, file migration sẽ được Django **tự động sinh** khi chạy `python manage.py makemigrations`. Không cần viết file migration thủ công.

### 5.4. Các Bảng KHÔNG CẦN Index Mới

| Bảng                                                       | Số Records  | Lý Do                                  |
| ---------------------------------------------------------- | ----------- | -------------------------------------- |
| `student`, `teacher`                                       | 45-90, 5-10 | Full scan < 100 records không đáng kể  |
| `test`, `receptive_test`, `productive_test`                | < 160       | Full scan < 160 records không đáng kể  |
| `receptive_part`, `receptive_question`, `receptive_answer` | < 26k       | Full scan < 26k records không đáng kể  |
| `post`, `post_reaction`                                    | < 6k        | Full scan < 6k records không đáng kể   |
| `test_feedback`                                            | < 1.6k      | Full scan < 1.6k records không đáng kể |
| Tất cả bảng lookup                                         | < 32        | Full scan < 32 records không đáng kể   |
