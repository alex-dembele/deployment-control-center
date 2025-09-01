from typing import Dict, List
import yaml

# Templates basés sur les fichiers
SERVICE_TEMPLATES = {
    "contract-api": {
        "isInternalService": True,
        "dns": "nexah.net",
        "application": {
            "genericName": "contract-api",
            "tier": "backend",
            "role": "api",
            "category": "nexah"
        },
        "container": {
            "image": "nexah/contract-api:{tag}"  # Placeholder pour tag
        },
        "secretEnvironmentVariables": {
            "Enabled": True,
            "Keys": [
                "NXH_DATABASE_HOST", "NXH_DATABASE_PORT", "NXH_DATABASE_NAME",
                "NXH_DATABASE_USER", "NXH_DATABASE_PASSWORD", "NXH_SHORTY_API_URL",
                "NXH_SHORTY_API_KEY", "NXH_SMS_API_URL", "NXH_SMS_API_TOKEN",
                "NXH_AWS_ACCESS_KEY_ID", "NXH_AWS_SECRET_ACCESS_KEY",
                "NXH_AWS_DEFAULT_REGION", "NXH_AWS_BUCKET",
                "NXH_AWS_USE_PATH_STYLE_ENDPOINT", "NXH_AWS_SUPPRESS_PHP_DEPRECATION_WARNING",
                "NXH_ORG_API_URL", "NXH_AUTH_API_URL", "NXH_APP_SLUG", "NXH_APP_ID"
            ]
        }
    },
    "contract-web-admin": {
        "isInternalService": False,
        "dns": "nexah.net",
        "application": {
            "genericName": "contract-web-admin",
            "tier": "backend",
            "role": "api",
            "category": "nexah"
        },
        "container": {
            "image": "nexah/contract-web-admin:{tag}"
        },
        "secretEnvironmentVariables": {
            "Enabled": True,
            "Keys": ["NXH_MS_CONTRACT_API_BASE_URL"]
        }
    },
    "retail-api": {
        "isInternalService": True,
        "dns": "nexah.net",
        "application": {
            "genericName": "retail-api",
            "tier": "backend",
            "role": "api",
            "category": "nexah"
        },
        "container": {
            "image": "nexah/retail-api:{tag}"
        },
        "secretEnvironmentVariables": {
            "Enabled": True,
            "Keys": [
                "NXH_DATABASE_HOST", "NXH_DATABASE_PORT", "NXH_DATABASE_NAME",
                "NXH_DATABASE_USER", "NXH_DATABASE_PASSWORD", "NXH_SHORTY_API_URL",
                "NXH_SHORTY_API_KEY", "NXH_SMS_API_URL", "NXH_SMS_API_TOKEN",
                "NXH_AWS_ACCESS_KEY_ID", "NXH_AWS_SECRET_ACCESS_KEY",
                "NXH_AWS_DEFAULT_REGION", "NXH_AWS_BUCKET",
                "NXH_AWS_USE_PATH_STYLE_ENDPOINT", "NXH_AWS_SUPPRESS_PHP_DEPRECATION_WARNING",
                "NXH_ORG_API_URL", "NXH_USER_API_URL", "NXH_SMS_API_BULK_URL"
            ]
        }
    },
    "retail-web-admin": {
        "isInternalService": True,
        "dns": "nexah.net",
        "application": {
            "genericName": "retail-web-admin",
            "tier": "backend",
            "role": "api",
            "category": "nexah"
        },
        "container": {
            "image": "nexah/retail-web-admin:{tag}"
        },
        "secretEnvironmentVariables": {
            "Enabled": True,
            "Keys": [
                "NXH_API_BASE_URL", "NXH_APP_ID", "NXH_AUTH_BASE_URL",
                "NXH_APP_BASE_URL", "NXH_MS_CMR_BASE_URL",
                "NXH_MS_SERVICE_API_BASE_URL", "NXH_MS_ORGANISATION_API_BASE_URL",
                "NXH_MS_VALIDATION_API_BASE_URL", "NXH_APP_NAME"
            ]
        }
    }
}

def get_service_template(service: str, tag: str) -> Dict:
    template = SERVICE_TEMPLATES.get(service, {})
    if not template:
        raise ValueError(f"Unknown service: {service}")
    template_copy = template.copy()
    template_copy["container"]["image"] = template_copy["container"]["image"].format(tag=tag)
    return template_copy

def get_service_env_keys(service: str) -> List[str]:
    template = SERVICE_TEMPLATES.get(service, {})
    return template.get("secretEnvironmentVariables", {}).get("Keys", [])

def update_appset_yaml(appset_path: str, service: str, env: str):
    with open(appset_path, "r") as f:
        appset = yaml.safe_load(f)
    
    # Vérifier si service existe
    elements = appset["spec"]["generators"][0]["list"]["elements"]
    service_entry = next((e for e in elements if e["name"] == f"nxh-{service}-ms"), None)
    values_file = f"nxh-{service}-ms-values.yaml"

    if not service_entry:
        # Ajouter nouveau service
        elements.append({
            "name": f"nxh-{service}-ms",
            "path": "04-nxh-services-ms",
            "nxhValuesFile": values_file
        })

    # Écrire mise à jour
    with open(appset_path, "w") as f:
        yaml.dump(appset, f)