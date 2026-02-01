"""Another sample Python file for testing."""


class DataProcessor:
    """Process data with various methods."""

    def __init__(self, data):
        self.data = data
        self.processed = []

    def process(self):
        """Main processing method."""
        for item in self.data:
            if self._validate(item):
                processed_item = self._transform(item)
                self.processed.append(processed_item)

    def _validate(self, item):
        """Validate an item."""
        if not item:
            return False
        if isinstance(item, dict):
            return 'id' in item and 'value' in item
        return True

    def _transform(self, item):
        """Transform an item."""
        if isinstance(item, dict):
            return {
                'id': item['id'],
                'value': item['value'] * 2,
                'processed': True
            }
        return item


def complex_decision_tree(age, income, credit_score, employment_status):
    """Complex decision tree with many branches."""
    if age < 18:
        return "rejected_underage"
    elif age >= 65:
        if income > 50000:
            return "approved_senior_high_income"
        else:
            return "review_senior_low_income"
    else:
        if employment_status == "employed":
            if credit_score >= 750:
                if income > 100000:
                    return "approved_premium"
                elif income > 50000:
                    return "approved_standard"
                else:
                    return "approved_basic"
            elif credit_score >= 650:
                if income > 75000:
                    return "approved_standard"
                else:
                    return "review_moderate_credit"
            else:
                return "rejected_low_credit"
        elif employment_status == "self_employed":
            if credit_score >= 700 and income > 75000:
                return "approved_self_employed"
            else:
                return "review_self_employed"
        else:
            return "rejected_unemployed"
