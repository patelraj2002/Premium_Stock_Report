# API keys
API_KEY = 'KECS0KY9GJMKIC3R'
BASE_URL = 'https://www.alphavantage.co/query'
EOD_API_TOKEN = '670e930c66a298.91756873'
os.environ["GROQ_API_KEY"] = "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"

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)