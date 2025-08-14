# ANP Format Implementation Documentation



# 生成智能体描述文档

ad.json返回的格式按照下面的定义来进行处理：
- 使用普通的json，不使用json-ld的格式
- Interface使用openrpc的格式，放到content字段中。
- Interface只处理Access level为external和both的接口。
- servers中的http请求的端点，使用一个配置的值。

{
  "protocolType": "ANP",
  "protocolVersion": "1.0.0",
  "type": "AgentDescription",
  "url": "https://hotel-services.com/agents/booking-assistant",
  "name": "Hotel Booking Assistant",
  "did": "did:wba:hotel-services.com:service:booking-assistant",
  "owner": {
    "type": "Organization",
    "name": "Hotel Services Group",
    "url": "https://hotel-services.com"
  },
  "description": "Hotel Booking Assistant with embedded OpenRPC interface for direct service access.",
  "created": "2024-12-31T12:00:00Z",
  "securityDefinitions": {
    "didwba_sc": {
      "scheme": "didwba",
      "in": "header",
      "name": "Authorization"
    }
  },
  "security": "didwba_sc",
  "interfaces": [
    {
      "type": "StructuredInterface",
      "protocol": "openrpc",
      "description": "OpenRPC interface for accessing hotel services.",
      "content": {
        "openrpc": "1.3.2",
        "info": {
          "title": "Hotel Booking Services API",
          "version": "2.0.0",
          "description": "Embedded OpenRPC API for hotel booking and management services"
        },
        "servers": [
            {
            "name": "Production Server",
            "url": "https://grand-hotel.com/api/v1/jsonrpc",
            "description": "Production server for Grand Hotel API"
            }
        ],
        "methods": [
          {
            "name": "checkAvailability",
            "summary": "Check room availability",
            "description": "Check availability of rooms for specified dates and criteria",
            "params": [
              {
                "name": "checkInDate",
                "description": "Check-in date in YYYY-MM-DD format",
                "required": true,
                "schema": {
                  "type": "string",
                  "format": "date"
                }
              },
              {
                "name": "checkOutDate",
                "description": "Check-out date in YYYY-MM-DD format",
                "required": true,
                "schema": {
                  "type": "string",
                  "format": "date"
                }
              },
              {
                "name": "guestCount",
                "description": "Number of guests",
                "required": true,
                "schema": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 10
                }
              },
              {
                "name": "roomPreferences",
                "description": "Room preferences and filters",
                "required": false,
                "schema": {
                  "$ref": "#/components/schemas/RoomPreferences"
                }
              }
            ],
            "result": {
              "name": "availabilityResult",
              "description": "Available rooms and pricing information",
              "schema": {
                "type": "object",
                "properties": {
                  "availableRooms": {
                    "type": "array",
                    "items": {
                      "$ref": "#/components/schemas/AvailableRoom"
                    }
                  },
                  "totalCount": {
                    "type": "integer",
                    "description": "Total number of available rooms"
                  }
                }
              }
            }
          },
          {
            "name": "createBooking",
            "summary": "Create a new booking",
            "description": "Create a new hotel booking with guest and payment information",
            "params": [
              {
                "name": "bookingDetails",
                "description": "Complete booking information",
                "required": true,
                "schema": {
                  "$ref": "#/components/schemas/BookingDetails"
                }
              }
            ],
            "result": {
              "name": "bookingResult",
              "description": "Booking confirmation and details",
              "schema": {
                "type": "object",
                "properties": {
                  "bookingId": {
                    "type": "string",
                    "description": "Unique booking identifier"
                  },
                  "confirmationCode": {
                    "type": "string",
                    "description": "Booking confirmation code"
                  },
                  "totalPrice": {
                    "type": "number",
                    "description": "Total booking price"
                  },
                  "status": {
                    "type": "string",
                    "enum": ["confirmed", "pending", "failed"]
                  }
                }
              }
            }
          }
        ],
        "components": {
          "schemas": {
            "RoomPreferences": {
              "type": "object",
              "properties": {
                "roomType": {
                  "type": "string",
                  "enum": ["standard", "deluxe", "suite", "presidential"],
                  "description": "Preferred room type"
                },
                "bedType": {
                  "type": "string",
                  "enum": ["single", "double", "queen", "king"],
                  "description": "Preferred bed type"
                },
                "smokingAllowed": {
                  "type": "boolean",
                  "description": "Whether smoking is allowed"
                },
                "maxPrice": {
                  "type": "number",
                  "description": "Maximum price per night"
                }
              }
            },
            "AvailableRoom": {
              "type": "object",
              "properties": {
                "roomId": {
                  "type": "string",
                  "description": "Unique room identifier"
                },
                "roomType": {
                  "type": "string",
                  "description": "Room type"
                },
                "pricePerNight": {
                  "type": "number",
                  "description": "Price per night"
                },
                "totalPrice": {
                  "type": "number",
                  "description": "Total price for the stay"
                },
                "amenities": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  },
                  "description": "List of room amenities"
                },
                "images": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  },
                  "description": "URLs of room images"
                }
              }
            },
            "BookingDetails": {
              "type": "object",
              "properties": {
                "roomId": {
                  "type": "string",
                  "description": "Selected room identifier"
                },
                "checkInDate": {
                  "type": "string",
                  "format": "date",
                  "description": "Check-in date"
                },
                "checkOutDate": {
                  "type": "string",
                  "format": "date",
                  "description": "Check-out date"
                },
                "guestInfo": {
                  "$ref": "#/components/schemas/GuestInfo"
                },
                "paymentInfo": {
                  "$ref": "#/components/schemas/PaymentInfo"
                },
                "specialRequests": {
                  "type": "string",
                  "description": "Special requests or notes"
                }
              },
              "required": ["roomId", "checkInDate", "checkOutDate", "guestInfo", "paymentInfo"]
            },
            "GuestInfo": {
              "type": "object",
              "properties": {
                "firstName": {
                  "type": "string",
                  "description": "Guest's first name"
                },
                "lastName": {
                  "type": "string",
                  "description": "Guest's last name"
                },
                "email": {
                  "type": "string",
                  "format": "email",
                  "description": "Guest's email address"
                },
                "phone": {
                  "type": "string",
                  "description": "Guest's phone number"
                },
                "address": {
                  "$ref": "#/components/schemas/Address"
                }
              },
              "required": ["firstName", "lastName", "email", "phone"]
            },
            "Address": {
              "type": "object",
              "properties": {
                "street": {
                  "type": "string",
                  "description": "Street address"
                },
                "city": {
                  "type": "string",
                  "description": "City"
                },
                "state": {
                  "type": "string",
                  "description": "State or province"
                },
                "zipCode": {
                  "type": "string",
                  "description": "ZIP or postal code"
                },
                "country": {
                  "type": "string",
                  "description": "Country"
                }
              },
              "required": ["street", "city", "country"]
            },
            "PaymentInfo": {
              "type": "object",
              "properties": {
                "cardNumber": {
                  "type": "string",
                  "description": "Credit card number"
                },
                "expiryMonth": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 12,
                  "description": "Card expiry month"
                },
                "expiryYear": {
                  "type": "integer",
                  "description": "Card expiry year"
                },
                "cvv": {
                  "type": "string",
                  "description": "Card verification value"
                },
                "cardholderName": {
                  "type": "string",
                  "description": "Name on the card"
                }
              },
              "required": ["cardNumber", "expiryMonth", "expiryYear", "cvv", "cardholderName"]
            }
          }
        }
      }
    }
}


# 怎么调用ad.json中的openrpc

当上面配置的端点收到请求的时候，根据json-rpc的内容，从agent router中找到对应的方法，进行调用。




## Overview

This document describes the implementation of the ANP (Agent Network Protocol) format for the Octopus multi-agent system, replacing the previous JSON-LD format with a cleaner, more standardized approach using OpenRPC.

## Key Changes

### 1. Agent Interface Access Levels

Added `access_level` field to agent interfaces with three possible values:
- **`internal`** (default): Only accessible within the agent system
- **`external`**: Only accessible via external API calls
- **`both`**: Accessible both internally and externally

#### Implementation in `router/agents_router.py`:
```python
@dataclass
class MethodInfo:
    # ... other fields ...
    access_level: str = "internal"  # "internal", "external", "both"
```

#### Usage in agent methods:
```python
@agent_interface(
    description="Send a message",
    access_level="both"  # Available both internally and externally
)
def send_message(self, ...):
    pass
```

### 2. ANP Format for `/ad.json`

The agent description now follows the ANP protocol format:

```json
{
  "protocolType": "ANP",
  "protocolVersion": "1.0.0",
  "type": "AgentDescription",
  "url": "http://localhost:8000/ad.json",
  "name": "Octopus Multi-Agent System",
  "did": "did:wba:octopus.ai:agents",
  "owner": {
    "type": "Organization",
    "name": "Octopus AI",
    "url": "http://localhost:8000"
  },
  "description": "...",
  "created": "2024-01-01T12:00:00Z",
  "securityDefinitions": {
    "didwba_sc": {
      "scheme": "didwba",
      "in": "header",
      "name": "Authorization"
    }
  },
  "security": "didwba_sc",
  "interfaces": [
    {
      "type": "StructuredInterface",
      "protocol": "openrpc",
      "description": "OpenRPC interface for accessing Octopus multi-agent services.",
      "content": {
        // OpenRPC specification
      }
    }
  ]
}
```

### 3. OpenRPC Interface Generation

Created `OpenRPCGenerator` class to convert agent methods to OpenRPC format:

```python
class OpenRPCGenerator:
    @staticmethod
    def generate_openrpc_interface(agents_list) -> Dict[str, Any]:
        # Generates OpenRPC specification with:
        # - Only external/both access level methods
        # - Proper parameter schemas
        # - JSON-RPC method names (agent.method format)
```

### 4. JSON-RPC Endpoint Access Control

The `/agents/jsonrpc` endpoint now enforces access levels:

```python
@router.post("/agents/jsonrpc")
async def handle_jsonrpc_call(request: JSONRPCRequest):
    # ... parse method name ...

    # Check if method is allowed for external access
    access_level = getattr(method_info, 'access_level', 'internal')
    if access_level not in ['external', 'both']:
        return JSONRPCResponse(
            error={"message": "Method not available for external access"}
        )
```

## Example: Message Agent Methods

The message agent demonstrates all three access levels:

1. **`both`** - Available internally and externally:
   - `send_message`
   - `get_statistics`

2. **`external`** - Only available via API:
   - `get_message_history`

3. **`internal`** - Only for internal use:
   - `receive_message`
   - `clear_history`

## Testing

Use the test script `test_anp_ad_json.py` to verify:
1. ANP format structure
2. OpenRPC content generation
3. Access level enforcement
4. JSON-RPC method calls

## Benefits

1. **Security**: Fine-grained control over which methods are exposed externally
2. **Standards Compliance**: Uses OpenRPC 1.3.2 specification
3. **Clarity**: Clear separation between internal and external APIs
4. **Flexibility**: Methods can be easily reconfigured for different access patterns

## Migration Notes

- Existing code continues to work as all methods default to `internal`
- To expose a method externally, explicitly set `access_level="external"` or `access_level="both"`
- The old JSON-LD format has been completely replaced with the ANP format
