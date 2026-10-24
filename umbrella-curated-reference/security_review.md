# Project UMBRELLA: Curation Security & Credential Audit Report

- Audit Timestamp: 2026-10-24T09:09:04.402989+00:00
- Repositories Audited: 4
- Total Files Screened: 8245
- Curated Files Retained: 2219
- Irrelevant / Bloat Files Excluded: 6026
- Potential Findings Flagged / Sanitized: 24

## Findings Detail

### `architecture\Infosys-Agentic-Foundry\docs\Installation\linux.md`
- **Hardcoded Password**: `PASSWORD='postgres'...`

### `architecture\Infosys-Agentic-Foundry\docs\Installation\windows.md`
- **Hardcoded Password**: `PASSWORD='postgres'...`

### `tests_and_examples\Infosys-Agentic-Foundry\IAF-Litellm-Server\constants.example.py`
- **Hardcoded Password**: `PASSWORD = "YOUR_PASSWORD"...`

### `source_code\Infosys-Agentic-Foundry\Infosys-Agentic-Foundry-Backend\.github\workflows\AKS-template.yml`
- **Hardcoded Password**: `password="$JFROG_TOKEN"...`

### `source_code\Infosys-Agentic-Foundry\Infosys-Agentic-Foundry-Backend\tool_chatbot\tools\get_code_with_version.py`
- **Potential API/Auth Token**: `auth_token="eyJhbGciOiJIUzI1NiIs..."...`

### `source_code\Infosys-Agentic-Foundry\site\search\search_index.json`
- **Hardcoded Password**: `PASSWORD='postgres'...`
- **Hardcoded Password**: `PASSWORD='postgres'...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-admin\Readme.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-backend\README.md`
- **Hardcoded Password**: `PWD = "${password}"...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-backend\backend-rai\tests\unit\mappers\test_user_mapper.py`
- **Hardcoded Password**: `Password="NewAbc@123"...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-backend\backend-rai\tests\unit\services\test_backend_service.py`
- **Hardcoded Password**: `password = "pass123"...`
- **Hardcoded Password**: `password = "pass123"...`
- **Hardcoded Password**: `password = "Pass@123"...`
- **Hardcoded Password**: `password = "Pass@123"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-explain\README.md`
- **Hardcoded Password**: `PWD = "${password}"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-Hallucination\README.md`
- **Potential API/Auth Token**: `API_KEY="your_openai_api_key"...`
- **Hardcoded Password**: `PWD="${password}"...`
- **Hardcoded Password**: `PWD="password123"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-model-detail\README.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-moderationlayer\README.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-moderationlayer\tests\90Tests\test_AdminDb.py`
- **Hardcoded Password**: `password="cosmospass"...`
- **Hardcoded Password**: `password="valid_pass"...`
- **Hardcoded Password**: `password="valid_pass"...`
- **Hardcoded Password**: `password="valid_pass"...`
- **Hardcoded Password**: `password="pgpass"...`
- **Hardcoded Password**: `password="pgpass"...`
- **Hardcoded Password**: `password="pgpass"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-moderationmodel\README.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-moderationmodel\models\restricted-deberta-base-zeroshot-v2\tokenizer.json`
- **Google API Key**: `AIZABwCH5AAAmmUAgJ5lAICiZQCApmUAgKplAIC...`
- **Google API Key**: `AIzACAhjgEAIdQAwAMzACAEMwAgBTMAIAYzACA4...`
- **AWS Access Key ID**: `AKiAIAGogCACqIAgLjpA...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-privacy\responsible-ai-privacy\tests\test_code_detect_service.py`
- **Potential API/Auth Token**: `api_key = "sk_live_1234567890"...`
- **Hardcoded Password**: `password = "P@ssw0rd!#$%"...`
- **Hardcoded Password**: `password: "MyP@ssw0rd123"...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-privacy\responsible-ai-privacy\tests\test_regexdetection.py`
- **Hardcoded Password**: `password = "password123"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-reporting-tool\README.md`
- **Hardcoded Password**: `PWD = "${password}"...`

### `tests_and_examples\Infosys-Responsible-AI-Toolkit\responsible-ai-telemetry\tests\service\test_resgisterservice.py`
- **Hardcoded Password**: `password = "secret"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-upload-doc\Readme.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `guardrails_and_safety\Infosys-Responsible-AI-Toolkit\responsible-ai-workbench\README.md`
- **Hardcoded Password**: `PWD="${password}"...`

### `source_code\Server-Patching-Tool\patchautomationEndpoints\properties.py`
- **Hardcoded Password**: `password = "<password>"...`

