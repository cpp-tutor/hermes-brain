import os
import yaml
import json
from pathlib import Path
from plugins.dashboard_auth.basic import hash_password, _verify_password

def main():
    # 1. Read existing 'config.yaml' creating an empty one if not present
    config_path = os.getenv('HERMES_HOME')
    if not config_path:
        print('ERROR: HERMES_HOME environment variable is not set.')
        return
    config_path += os.sep + 'config.yaml'

    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            try:
                config = yaml.safe_load(f) or {}
                write_config = False
            except yaml.YAMLError as e:
                print('ERROR: Error parsing existing config.yaml - please edit or remove it.')
                return
    else:
        config = {}
        write_config = True
        print('INFO: Creating new config.yaml.')

    # 2. Check existing password and password hash match those in environment, updating if different
    password = os.getenv('HERMES_WEBUI_PASSWORD')
    if not password:
        print('INFO: HERMES_WEBUI_PASSWORD environment variable is not set.')
        print('INFO: In config.yaml, "basic_auth:" in "dashboard:" will not be modified.')
    username = os.getenv('HERMES_WEBUI_USERNAME')
    if not username:
        print('INFO: HERMES_WEBUI_USERNAME environment variable is not set.')
        print('INFO: Defaulting to "admin".')
        username = 'admin'

    if password:
        hashed_password = hash_password(password)
        if 'dashboard' not in config or config['dashboard'] is None:
            config['dashboard'] = {}
        if 'basic_auth' not in config['dashboard'] or config['dashboard']['basic_auth'] is None:
            config['dashboard']['basic_auth'] = {}

        if 'username' not in config['dashboard']['basic_auth'] or username != config['dashboard']['basic_auth']['username']:
            config['dashboard']['basic_auth']['username'] = username
            write_config = True
            print('INFO: Username updated.')
        if 'password_hash' not in config['dashboard']['basic_auth'] or not _verify_password(password, config['dashboard']['basic_auth']['password_hash']):
            config['dashboard']['basic_auth']['password_hash'] = hashed_password
            write_config = True
            print('INFO: Password hash updated.')

    # 3. Create configuration for Docker MCP Gateway if not present, and update token if changed
    mcp_auth_token = os.getenv('MCP_GATEWAY_AUTH_TOKEN')
    if mcp_auth_token:
        if 'mcp_servers' not in config or config['mcp_servers'] is None:
            config['mcp_servers'] = {}
        if 'docker_gateway' not in config['mcp_servers'] or config['mcp_servers']['docker_gateway'] is None:
            config['mcp_servers']['docker_gateway'] = {}
            config['mcp_servers']['docker_gateway']['url'] = 'http://mcp-gateway:8811/sse'
            config['mcp_servers']['docker_gateway']['transport'] = 'sse'
            config['mcp_servers']['docker_gateway']['headers'] = {}
            config['mcp_servers']['docker_gateway']['headers']['Authorization'] = f'Bearer {mcp_auth_token}'
            config['mcp_servers']['docker_gateway']['enabled'] = 'true'
            write_config = True
            print('INFO: Configuration for "docker_gateway:" added to "mcp_servers:".')

        # If docker_gateway already defined, only write to config.yaml if 'Authorization:' has changed
        elif 'headers' in config['mcp_servers']['docker_gateway'] and config['mcp_servers']['docker_gateway']['headers'] is not None:
            if 'Authorization' in config['mcp_servers']['docker_gateway']['headers'] and config['mcp_servers']['docker_gateway']['headers']['Authorization'] is not None:
                if f'Bearer {mcp_auth_token}' != config['mcp_servers']['docker_gateway']['headers']['Authorization']:
                    config['mcp_servers']['docker_gateway']['headers']['Authorization'] = f'Bearer {mcp_auth_token}'
                    write_config = True
                    print('INFO: "Authorization:" for "docker_gateway:" updated.')

    # 4. Create configuration for Docker Model Runner if not present, and update context_length if changed
    api_name = 'Docker Model Runner'
    api_endpoint = os.getenv('LLM_API_ENDPOINT')
    api_key = os.getenv('LLM_API_KEY')
    api_model = os.getenv('LLM_API_MODEL', '')
    api_context = os.getenv('LLM_CONTEXT_LENGTH')
    if api_endpoint and api_key:
        if 'custom_providers' not in config or config['custom_providers'] is None:
            config['custom_providers'] = []
        for provider in config['custom_providers']:
            if 'name' in provider and provider['name'] == api_name:
                if 'base_url' not in provider or provider['base_url'] != api_endpoint:
                    provider['base_url'] = api_endpoint
                    provider['api_key'] = api_key
                    provider['model'] = api_model
                    write_config = True
                    print(f'INFO: Custom URL changed to: {api_endpoint}')
                if api_context and ('context_length' not in provider or provider['context_length'] != int(api_context)):
                    provider['context_length'] = int(api_context)
                    write_config = True
                    print(f'INFO: Context length changed to: {api_context}')
                break
        else:
            provider_count = len(config['custom_providers'])
            config['custom_providers'].append({})
            config['custom_providers'][provider_count]['name'] = api_name
            config['custom_providers'][provider_count]['base_url'] = api_endpoint
            config['custom_providers'][provider_count]['key'] = api_key
            config['custom_providers'][provider_count]['model'] = api_model
            if api_context:
                config['custom_providers'][provider_count]['context_length'] = int(api_context)
            write_config = True
            print(f'INFO: Added custom URL: {api_endpoint}')

    # 5. Set chat model name and use Docker Model Runner if set in environment
    if api_model:
        if 'model' not in config or config['model'] is None:
            config['model'] = {}
        if 'default' not in config['model'] or config['model']['default'] != api_model:
            config['model']['base_url'] = api_endpoint
            config['model']['default'] = api_model
            config['model']['provider'] = 'custom'
            config['model']['api_key'] = api_key
            write_config = True
            print(f'INFO: Default model changed to: {api_model}')

    # 6. Configure Hermes to use Hindsight memory backend if set in environment
    memory_api=os.getenv('HERMES_USE_HINDSIGHT')
    if memory_api and memory_api != 'false':
        if 'memory' not in config or config['memory'] is None:
            config['memory'] = {}
        if 'provider' not in config['memory'] or config['memory']['provider'] != 'hindsight':
            config['memory']['provider'] = 'hindsight'
            config['memory']['memory_enabled'] = 'true'
            config['memory']['user_profile_enabled'] = 'true'
            write_config = True
            print('INFO: Hindsight memory manager enabled.')

            # Create /home/hermes/.hermes/hindsight/config.json if not present
            hindsight_config_path = os.getenv('HERMES_HOME') + os.sep + 'hindsight'
            Path(hindsight_config_path).mkdir(exist_ok=True)
            hindsight_config_path += os.sep + 'config.json'
            if not Path(hindsight_config_path).exists():
                hindsight_config = {}
                hindsight_config.update({
                    "mode": "local_external",
                    "api_url": "http://hindsight:8888",
                    "bank_id": "hermes",
                    "api_key": os.getenv('HINDSIGHT_API_KEY', ''),
                    "timeout": 120,
                    "idle_timeout": 300,
                    "retain_tags": "",
                    "observation_scopes": "",
                    "retain_source": "",
                    "retain_user_prefix": "User",
                    "retain_assistant_prefix": "Assistant",
                    "banks": {
                        "hermes": {
                            "bankId": "hermes",
                            "budget": "mid",
                            "enabled": True
                        }
                    },
                    "recall_budget": "mid"
                })
                try:
                    with open(hindsight_config_path, "w", encoding="utf-8") as f:
                        json.dump(hindsight_config, f, indent=2)
                    print(f'INFO: Created: {hindsight_config_path}')
                except:
                    print(f'WARN: Could not create file: {hindsight_config_path}')
    else:
        if 'memory' not in config or config['memory'] is None:
            config['memory'] = {}
        if 'provider' in config['memory'] and config['memory']['provider'] == 'hindsight':
            config['memory']['provider'] = ''
            config['memory']['memory_enabled'] = 'true'
            config['memory']['user_profile_enabled'] = 'true'
            write_config = True
            print('INFO: Hindsight memory manager disabled.')
            hindsight_config_path = os.getenv('HERMES_HOME') + os.sep + 'hindsight' + os.sep + 'config.json'
            if Path(hindsight_config_path).exists():
                Path(hindsight_config_path).rename(hindsight_config_path + '.old')
                print(f'INFO: Renamed: {hindsight_config_path} as {hindsight_config_path}.old')

    # 7. Write out config file if flagged as changed
    if write_config == True:
        try:
            with open(config_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            print('INFO: Updated: config.yaml.')
        except:
            print('WARN: Could not update file: config.yaml')
    else:
        print('INFO: No changes to config.yaml')

if __name__ == '__main__':
    main()