from jsonschema import validate

# https://json-schema.org/learn/getting-started-step-by-step#going-deeper-with-properties

NotificationServices_schema = {
    "type": "object",
    "properties": {
        "ProfileName": {"type": "string"},
        "Type": {"type": "string"},
        "Webhook": {"type": "string"},
        "UserName": {"type": "string"},
        "BearerToken": {"type": "string"},
        "ApiKey": {"type": "string"},
        "ApiKeySecret": {"type": "string"},
        "AccessToken": {"type": "string"},
        "AccessTokenSecret": {"type": "string"},
        "ClientKey": {"type": "string"},
        "ClientSecret": {"type": "string"},
        "AccessToken": {"type": "string"},
        "BaseURL": {"type": "string"},
        "emails": {"type": "array"},
    },
    
    "required": ["ProfileName", "Type"],# can this do conditional requirements?
    "additionalProperties": False
}

filters_schema = {
    "type": "object",
    # TODO: lots of properties...
}

Searches_schema = {
    "type": "object",
    "properties": {
        "GameName": {"type": "string"},
        "UserName": {"type": "string"},
        "filters": {"type": "array", "items":filters_schema},
        "Notifications": {"type": "array"},
        "CustomDiscordMessage": {"type": "string"},
        "TitleOverride": {"type": "string"},
    },

    "required": ["Notifications"], # can this do conditional requirements?
    "additionalProperties": False
}

base_schema = {
    "type" : "object",
     "properties" : {
        "clientId": {"type" : "string"},
        "accessToken": {"type" : "string"},
        "IgnoreStreams": {"type": "array", "items":{"type": "string"}},
        "CooldownSeconds": {"type": "number"},

        "NotificationServices": {"type": "array", "items": NotificationServices_schema},
        "ErrorNotifications": {"type": "array", "items":{"type": "string"}},

        "Searches": { "type": "array", "items": Searches_schema },
     },

     "required": ["clientId", "accessToken", "CooldownSeconds", "NotificationServices", "Searches"],
     "additionalProperties": False
}

def validateConfig(conf):
    global base_schema
    validate(conf, base_schema)

    assert conf.get('clientId'), 'config has clientId'
    assert conf.get('accessToken'), 'config has accessToken'
    assert conf.get('Searches'), 'config has Searches'
    assert conf.get('NotificationServices'), 'config has NotificationServices'

    for search in conf.get('Searches',[]):
        # Must have one but not both
        assert ("GameName" in search) ^ ("UserName" in search), 'testing config for search: ' + repr(search)
        
    for service in conf.get('NotificationServices',[]):
        assert service.get("ProfileName"), 'testing notification service for: ' + repr(service)
        assert service.get("Type"), 'testing notification service for: ' + repr(service)
        
        if service.get("Type")=="Twitter":
            assert service.get("ApiKey"), 'testing twitter config for: ' + repr(service)
            assert len(service.get("ApiKey")) == 25, 'testing twitter config for: ' + repr(service)
            assert '-' not in service.get("ApiKey"), 'testing twitter config for: ' + repr(service)

            assert service.get("ApiKeySecret"), 'testing twitter config for: ' + repr(service)
            assert len(service.get("ApiKeySecret")) == 50, 'testing twitter config for: ' + repr(service)
            assert'-' not in service.get("ApiKeySecret"), 'testing twitter config for: ' + repr(service)

            assert service.get("AccessToken"), 'testing twitter config for: ' + repr(service)
            assert len(service.get("AccessToken")) == 50, 'testing twitter config for: ' + repr(service)
            assert '-' in service.get("AccessToken"), 'testing twitter config for: ' + repr(service)

            assert service.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(service)
            assert len(service.get("AccessTokenSecret")) == 45, 'testing twitter config for: ' + repr(service)
            assert '-' not in service.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(service)

            assert service.get("BearerToken"), 'testing twitter config for: ' + repr(service)
            assert len(service.get("BearerToken")) > 60, 'testing twitter config for: ' + repr(service)
            assert '-' not in service.get("BearerToken"), 'testing twitter config for: ' + repr(service)
            
        elif service.get("Type")=="Discord":
            assert service.get("Webhook"), 'testing discord config for: ' + repr(service)
            assert service.get("UserName"), 'testing discord config for: ' + repr(service)
        elif service.get("Type")=="Pushbullet":
            assert service.get("ApiKey"), 'testing pushbullet config for: ' + repr(service)
        elif service.get("Type")=="Mastodon":
            assert service.get("ClientKey"), 'testing mastodon config for: ' + repr(service)
            assert service.get("ClientSecret"), 'testing mastodon config for: ' + repr(service)
            assert service.get("AccessToken"), 'testing mastodon config for: ' + repr(service)
            assert service.get("BaseURL"), 'testing mastodon config for: ' + repr(service)
