import json
from .client import complete
from .prompts import REVIEW
from .schemas import ReviewOutput

def review(data):
    result = json.loads(complete(REVIEW, json.dumps(data, default=str, ensure_ascii=False)))
    return ReviewOutput.model_validate(result)
