from ..models import ReceptivePart, ReceptiveQuestion


def calculate_scores(receptive_test):
    """
    Calculate and update scores for parts and total score for a given ReceptiveTest.

    This function:
    - Calculates score for each part as the sum of scores of its questions.
    - Calculates total_score as the sum of scores of all parts.

    Args:
        receptive_test: The ReceptiveTest instance to calculate scores for.
    """
    # Fetch fresh parts with questions to avoid stale prefetched data
    parts = ReceptivePart.objects.filter(
        receptive_test=receptive_test
    ).prefetch_related("receptive_questions")
    total_score = 0

    for part in parts:
        part_score = sum(question.score for question in part.receptive_questions.all())
        part.score = part_score
        total_score += part_score

    # Bulk update part scores
    ReceptivePart.objects.bulk_update(parts, ["score"])

    # Update total score
    receptive_test.total_score = total_score
    receptive_test.save()
