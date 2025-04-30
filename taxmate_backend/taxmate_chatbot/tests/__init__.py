class UserQuery:
    def __init__(self, question):
        self.question = question

def test_user_query_model():
    query = UserQuery("How to calculate tax?")
    assert query.question == "How to calculate tax?"