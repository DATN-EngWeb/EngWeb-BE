from ..models import ReceptivePart, ReceptiveQuestion


def renumber_receptive_test(receptive_test):
    """
    Renumber the order of parts and question numbers in ascending order for a given ReceptiveTest.

    This function ensures that:
    - Parts are ordered sequentially starting from 1 based on their current order.
    - Questions are numbered sequentially within each part starting from 1,
      sorted by current question_number.

    Args:
        receptive_test: The ReceptiveTest instance to renumber.
    """
    # Get all parts for the test, sorted by current order
    parts = list(receptive_test.receptive_parts.all().order_by("order"))

    # Renumber parts
    for new_order, part in enumerate(parts, start=1):
        part.order = new_order

    # Bulk update part orders
    ReceptivePart.objects.bulk_update(parts, ["order"])

    # Renumber questions within each part starting from 1
    for part in parts:
        questions_in_part = list(part.receptive_questions.all().order_by("question_number"))
        for new_q_num, question in enumerate(questions_in_part, start=1):
            question.question_number = new_q_num
        # Bulk update questions for this part
        ReceptiveQuestion.objects.bulk_update(questions_in_part, ["question_number"])
