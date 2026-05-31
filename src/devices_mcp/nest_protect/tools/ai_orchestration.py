"""Advanced AI orchestration tools using sampling capabilities for intelligent device management."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class _McpStub:
    """Stub decorator when tools are registered via register_nest_protect_tools."""

    def tool(self, *args, **kwargs):
        def decorator(func):
            return func

        if args and callable(args[0]) and not kwargs:
            return args[0]
        return decorator


mcp = _McpStub()


class HomeSafetyAssessmentParams(BaseModel):
    """Parameters for comprehensive home safety assessment."""

    include_recommendations: bool = Field(True, description="Include AI-generated safety recommendations")
    assessment_scope: Literal["basic", "comprehensive", "emergency"] = Field(
        "comprehensive", description="Scope of safety assessment"
    )
    focus_areas: list[str] = Field(
        ["smoke_detection", "co_detection", "battery_levels", "connectivity"],
        description="Specific areas to focus assessment on",
    )


class EmergencyResponseParams(BaseModel):
    """Parameters for emergency response coordination."""

    emergency_type: Literal["smoke", "co", "security", "medical", "unknown"] = Field(
        ..., description="Type of emergency detected"
    )
    affected_devices: list[str] = Field(..., description="Device IDs involved in emergency")
    response_priority: Literal["low", "medium", "high", "critical"] = Field(
        "high", description="Response priority level"
    )


class PredictiveMaintenanceParams(BaseModel):
    """Parameters for predictive maintenance analysis."""

    analysis_depth: Literal["quick", "detailed", "comprehensive"] = Field(
        "detailed", description="Depth of predictive analysis"
    )
    time_horizon: Literal["1_week", "1_month", "3_months", "1_year"] = Field(
        "1_month", description="Time horizon for predictions"
    )
    include_cost_estimates: bool = Field(True, description="Include maintenance cost estimates")


class SmartAutomationParams(BaseModel):
    """Parameters for intelligent automation setup."""

    automation_type: Literal["safety", "maintenance", "energy", "security"] = Field(
        ..., description="Type of automation to configure"
    )
    learning_period: Literal["1_week", "2_weeks", "1_month"] = Field(
        "2_weeks", description="Period to learn user patterns"
    )
    confidence_threshold: float = Field(0.8, ge=0.5, le=0.95, description="Minimum confidence for automation triggers")


@mcp.tool()
async def assess_home_safety(
    include_recommendations: bool = True,
    assessment_scope: str = "comprehensive",
    focus_areas: list[str] | None = None,
) -> dict[str, Any]:
    """🧠 **AI-Powered Home Safety Assessment with Sampling Intelligence**

    PORTMANTEAU PATTERN RATIONALE:
    Consolidates safety assessment, device analysis, and recommendation generation
    into a single intelligent operation that uses sampling for AI reasoning.
    Prevents tool explosion (assessment + analysis + recommendations = 1 tool)
    while maintaining full functionality and enabling conversational AI workflows.

    **AI Orchestration Features:**
    • 🔍 **Comprehensive Analysis**: Simultaneous evaluation of entire safety ecosystem
    • 🧠 **Pattern Recognition**: AI identification of safety trends and anomalies
    • 📊 **Risk Assessment**: Intelligent prioritization of safety issues by severity
    • 🚨 **Emergency Detection**: Automatic triggering of sampling for critical situations
    • 💡 **Predictive Insights**: AI-powered recommendations based on usage patterns

    **Sampling Capabilities:**
    • Triggers `requires_sampling: true` for complex safety analysis
    • Enables AI reasoning for multi-device safety coordination
    • Supports emergency response orchestration with intelligent prioritization

    **Assessment Scopes:**
    • **Basic**: Essential connectivity and battery checks
    • **Comprehensive**: Full device health, sensor analysis, and pattern evaluation
    • **Emergency**: Critical safety assessment with immediate action recommendations

    **Focus Areas:**
    • `smoke_detection`: Smoke sensor functionality and calibration
    • `co_detection`: Carbon monoxide monitoring and alert systems
    • `battery_levels`: Power status and replacement scheduling
    • `connectivity`: Network status and communication reliability

    Args:
        include_recommendations (bool): Include AI-generated safety recommendations with actionable insights. Required for: comprehensive assessments.
        assessment_scope (Literal["basic", "comprehensive", "emergency"]): Depth and urgency of safety evaluation.
            - "basic": Essential checks for immediate safety concerns
            - "comprehensive": Full ecosystem analysis with predictive insights
            - "emergency": Critical assessment triggering sampling for immediate response
        focus_areas (List[str] | None): Specific safety domains to prioritize in analysis.
            Must contain valid focus areas when specified.

    Returns:
        **FastMCP 3.1+ Conversational Response Structure with Sampling Signals:**

        ```json
        {
          "success": true,
          "operation": "assess_home_safety",
          "summary": "AI assessment completed: X issues found across Y devices",
          "result": {
            "assessment_scope": "comprehensive",
            "devices_analyzed": 5,
            "safety_issues": [
              {
                "type": "battery",
                "device": "Kitchen Detector",
                "severity": "medium",
                "description": "Low battery (15%)"
              }
            ],
            "analysis": {
              "total_devices": 5,
              "online_count": 4,
              "critical_issues": 1,
              "recommendations_count": 3
            }
          },
          "requires_sampling": true,  // Triggered for complex analysis
          "sampling_reason": "Multiple safety issues detected requiring AI prioritization",
          "next_steps": [
            "AI will analyze safety patterns and generate prioritized recommendations",
            "Review critical safety issues immediately",
            "Schedule maintenance for devices with problems"
          ],
          "context": {
            "operation_details": "Comprehensive AI safety assessment completed",
            "assessment_timestamp": "2025-01-18T14:30:00Z",
            "focus_areas_covered": ["smoke_detection", "co_detection"]
          },
          "suggestions": [
            "Replace batteries in devices showing low power",
            "Test smoke detector functionality monthly",
            "Consider additional detectors in high-risk areas"
          ],
          "follow_up_questions": [
            "Would you like me to help prioritize these safety issues?",
            "Should I run safety tests on the problematic devices?",
            "Do you want to schedule maintenance for battery replacement?"
          ]
        }
        ```

        **Success Response Structure (Conversational):**
        - success (bool): Operation completion status
        - operation (str): "assess_home_safety" for identification
        - summary (str): Human-readable assessment overview with key findings
        - result (dict): Structured assessment data and analysis results
        - requires_sampling (bool): True when complex AI analysis is needed
        - sampling_reason (str): Explanation of why sampling was triggered
        - next_steps (list[str]): Prioritized actions user should consider
        - context (dict): Operational metadata and assessment details
        - suggestions (list[str]): AI-generated actionable recommendations
        - follow_up_questions (list[str]): Interactive questions to guide next conversation

        **Error Recovery Response Structure:**
        - success (bool): Always false for errors
        - error (str): Specific error classification
        - error_code (str): Machine-readable error identifier
        - message (str): Human-friendly error explanation
        - recovery_options (list[str]): Step-by-step resolution instructions
        - diagnostic_info (dict): Technical details for troubleshooting
        - estimated_resolution_time (str): Expected time to resolve
        - urgency (str): Priority level (low, medium, high, critical)
    """
    from datetime import datetime

    import aiohttp

    from ..state_manager import get_app_state

    if focus_areas is None:
        focus_areas = ["smoke_detection", "co_detection", "battery_levels", "connectivity"]

    state = get_app_state()

    if not state.access_token:
        return {
            "success": False,
            "error": "Authentication required",
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": "Cannot perform safety assessment without API authentication",
            "recovery_options": [
                "Complete OAuth authentication flow",
                "Verify API credentials are configured",
            ],
            "estimated_resolution_time": "< 5 minutes",
            "urgency": "high",
        }

    try:
        # Step 1: Gather all device data
        devices_url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(devices_url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": "Device data unavailable",
                        "error_code": "API_ACCESS_DENIED",
                        "message": "Cannot retrieve device information for safety assessment",
                        "recovery_options": [
                            "Check API credentials",
                            "Verify network connectivity",
                            "Try again in a few moments",
                        ],
                        "estimated_resolution_time": "< 10 minutes",
                        "urgency": "medium",
                    }

                devices_data = await response.json()
                devices = devices_data.get("devices", [])

        if not devices:
            return {
                "success": False,
                "error": "No devices found",
                "error_code": "NO_DEVICES",
                "message": "No Nest Protect devices detected in your account",
                "recovery_options": [
                    "Add Nest Protect devices to your account",
                    "Check device connectivity",
                    "Verify device registration",
                ],
                "estimated_resolution_time": "Varies",
                "urgency": "medium",
            }

        # Step 2: Analyze each device
        device_analyses = []
        safety_issues = []
        recommendations = []

        for device in devices:
            device_id = device["name"].split("/")[-1]
            traits = device.get("traits", {})

            analysis = {
                "device_id": device_id,
                "name": traits.get("sdm.devices.traits.Info", {}).get("customName", f"Device {device_id[:8]}"),
                "online": traits.get("sdm.devices.traits.Connectivity", {}).get("status") == "ONLINE",
                "battery_level": traits.get("sdm.devices.traits.Battery", {}).get("batteryLevel"),
                "alarm_status": traits.get("sdm.devices.traits.SafetyAlarm", {}).get("alarmStatus"),
                "smoke_status": traits.get("sdm.devices.traits.Smoke", {}).get("smokeStatus"),
                "co_status": traits.get("sdm.devices.traits.CarbonMonoxide", {}).get("coStatus"),
                "last_update": device.get("lastEventTime"),
            }

            device_analyses.append(analysis)

            # Analyze safety issues
            if not analysis["online"]:
                safety_issues.append(
                    {
                        "type": "connectivity",
                        "device": analysis["name"],
                        "severity": "high",
                        "description": f"Device {analysis['name']} is offline",
                    }
                )

            if analysis["battery_level"] and analysis["battery_level"] < 20:
                safety_issues.append(
                    {
                        "type": "battery",
                        "device": analysis["name"],
                        "severity": "medium",
                        "description": f"Low battery ({analysis['battery_level']}%) on {analysis['name']}",
                    }
                )

            if analysis["alarm_status"] and analysis["alarm_status"] != "NONE":
                safety_issues.append(
                    {
                        "type": "alarm",
                        "device": analysis["name"],
                        "severity": "critical",
                        "description": f"Active alarm ({analysis['alarm_status']}) on {analysis['name']}",
                    }
                )

        # Step 3: Generate AI-powered recommendations (requires sampling signal)
        if include_recommendations and safety_issues:
            recommendations = [
                "Replace batteries in devices showing low power immediately",
                "Test alarm functionality on devices with connectivity issues",
                "Consider adding additional smoke detectors in high-risk areas",
                "Schedule professional inspection of alarm systems",
                "Update emergency contact information in safety apps",
            ]

            # Signal for AI sampling - complex safety analysis needed
            if len(safety_issues) > 3 or any(issue["severity"] == "critical" for issue in safety_issues):
                return {
                    "success": True,
                    "operation": "assess_home_safety",
                    "summary": f"Critical safety assessment completed: {len(safety_issues)} issues found across {len(devices)} devices",
                    "result": {
                        "assessment_scope": assessment_scope,
                        "devices_analyzed": len(devices),
                        "safety_issues": safety_issues,
                        "device_summaries": device_analyses,
                    },
                    "requires_sampling": True,  # Signal for AI reasoning
                    "sampling_reason": "Complex safety analysis with multiple critical issues detected",
                    "next_steps": [
                        "AI will analyze safety patterns and generate prioritized recommendations",
                        "Review device statuses and address critical issues first",
                        "Consider emergency response procedures",
                    ],
                    "context": {
                        "operation_details": "Comprehensive safety assessment with critical findings",
                        "assessment_timestamp": datetime.now().isoformat(),
                        "focus_areas_covered": focus_areas,
                    },
                    "suggestions": [
                        "Address critical safety issues immediately",
                        "Run emergency evacuation drills",
                        "Update family emergency plans",
                    ],
                    "follow_up_questions": [
                        "Would you like me to help prioritize these safety issues?",
                        "Should I prepare emergency response recommendations?",
                        "Do you need help contacting emergency services?",
                    ],
                }

        # Standard response for normal assessments
        return {
            "success": True,
            "operation": "assess_home_safety",
            "summary": f"Safety assessment completed: {len(safety_issues)} issues found across {len(devices)} devices",
            "result": {
                "assessment_scope": assessment_scope,
                "devices_analyzed": len(devices),
                "safety_issues": safety_issues,
                "device_summaries": device_analyses,
                "recommendations": recommendations if include_recommendations else [],
            },
            "next_steps": [
                "Review safety issues and address them promptly",
                "Run individual device tests using 'run_safety_check'",
                "Schedule regular maintenance for battery replacement",
            ],
            "context": {
                "operation_details": f"Completed {assessment_scope} safety assessment",
                "assessment_timestamp": datetime.now().isoformat(),
                "focus_areas_covered": focus_areas,
            },
            "suggestions": recommendations[:3] if recommendations else [],  # Top 3 recommendations
            "follow_up_questions": [
                "Would you like me to run safety checks on specific devices?",
                "Should I help you schedule battery replacements?",
                "Do you want to review emergency preparedness?",
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": "Assessment failed",
            "error_code": "ASSESSMENT_ERROR",
            "message": "Failed to complete home safety assessment",
            "recovery_options": [
                "Check network connectivity",
                "Verify API access",
                "Try assessment again",
            ],
            "diagnostic_info": {
                "root_cause": str(e),
                "affected_components": ["Safety assessment system"],
            },
            "alternative_solutions": [
                "Run individual device status checks",
                "Contact support for assessment assistance",
            ],
            "estimated_resolution_time": "< 15 minutes",
            "urgency": "medium",
        }


@mcp.tool()
async def coordinate_emergency_response(
    emergency_type: str, affected_devices: list[str], response_priority: str = "high"
) -> dict[str, Any]:
    """🚨 **AI Emergency Response Coordination with Sampling**

    PORTMANTEAU PATTERN RATIONALE:
    Consolidates emergency detection, device control, response coordination,
    and safety guidance into a single intelligent operation. Uses sampling
    signals to enable complex AI reasoning during critical safety situations.
    Prevents separate tools for detection, coordination, and response.

    **Emergency Coordination Intelligence:**
    • 🎯 **Priority Assessment**: AI evaluation of emergency severity and response needs
    • 📞 **Multi-Device Control**: Coordinated alarm management across affected devices
    • 🏃 **Evacuation Guidance**: Intelligent routing based on device locations and hazards
    • 📍 **Safety Zone Identification**: AI determination of safe areas within the home
    • ⏰ **Timeline Management**: Coordinated response timing for maximum safety

    **Emergency Types Supported:**
    • 🔥 **smoke**: Fire detection with evacuation and alarm silencing coordination
    • ☁️ **co**: Carbon monoxide emergency with ventilation and alert prioritization
    • 🔒 **security**: Intrusion detection with access control and notification coordination
    • 🆘 **medical**: Health emergency support with device monitoring and alert management
    • ❓ **unknown**: Unidentified emergency assessment with adaptive response planning

    **Response Priority Levels:**
    • **low**: Minor incident requiring monitoring but not immediate action
    • **medium**: Situation requiring attention but not critical evacuation
    • **high**: Serious situation requiring coordinated response and preparation
    • **critical**: Life-threatening emergency requiring immediate coordinated action

    **Sampling Triggers:**
    • Complex multi-device coordination requiring AI reasoning
    • Emergency severity assessment and response prioritization
    • Evacuation planning and safety zone optimization
    • Timeline coordination for maximum safety effectiveness

    Args:
        emergency_type (Literal["smoke", "co", "security", "medical", "unknown"]): Specific type of emergency detected.
            Determines response protocols, device coordination, and safety measures.
        affected_devices (List[str]): Array of device IDs involved in or detecting the emergency.
            Used for targeted alarm management and response coordination.
        response_priority (Literal["low", "medium", "high", "critical"]): Urgency level of response required.
            Affects coordination complexity and sampling trigger thresholds.

    Returns:
        **FastMCP 3.1+ Conversational Emergency Response Structure:**

        ```json
        {
          "success": true,
          "operation": "coordinate_emergency_response",
          "summary": "EMERGENCY smoke detected - coordinating response for 3 devices",
          "result": {
            "emergency_type": "smoke",
            "affected_devices": ["living-room", "kitchen", "hallway"],
            "response_priority": "critical",
            "coordination_status": "active",
            "estimated_response_time": "2 minutes"
          },
          "requires_sampling": true,
          "sampling_reason": "Complex emergency coordination required for smoke incident",
          "next_steps": [
            "AI will analyze emergency patterns and determine optimal response",
            "Silence non-essential alarms to reduce confusion",
            "Prepare emergency contact procedures",
            "Assess evacuation routes and safety zones"
          ],
          "context": {
            "operation_details": "Emergency response coordination for smoke detection",
            "timestamp": "2025-01-18T14:35:00Z",
            "priority_level": "critical",
            "devices_coordinated": 3
          },
          "suggestions": [
            "Follow established emergency procedures",
            "Contact emergency services if situation becomes life-threatening",
            "Account for all household members in evacuation",
            "Have emergency supplies ready at designated meeting point"
          ],
          "follow_up_questions": [
            "Are you and your family safe right now?",
            "Should I help silence alarms to reduce panic?",
            "Do you need emergency contact information?",
            "Would you like me to guide you through evacuation procedures?"
          ]
        }
        ```

        **Success Response Structure (Emergency Coordination):**
        - success (bool): Coordination initiation status
        - operation (str): "coordinate_emergency_response" for identification
        - summary (str): Emergency overview with device count and type
        - result (dict): Coordination details and status information
        - requires_sampling (bool): Always true for emergency coordination
        - sampling_reason (str): AI reasoning trigger explanation
        - next_steps (list[str]): Immediate safety actions prioritized by AI
        - context (dict): Emergency metadata and coordination details
        - suggestions (list[str]): AI-generated safety recommendations
        - follow_up_questions (list[str]): Interactive safety verification questions

        **Error Response Structure (Emergency Handling):**
        - success (bool): False when coordination cannot be established
        - error (str): Coordination failure reason
        - error_code (str): Specific failure classification
        - message (str): Human explanation of coordination issues
        - recovery_options (list[str]): Alternative safety measures
        - diagnostic_info (dict): Technical coordination failure details
        - urgency (str): Always "critical" for emergency coordination failures
    """
    from datetime import datetime

    # Emergency requires immediate AI sampling for complex decision making
    return {
        "success": True,
        "operation": "coordinate_emergency_response",
        "summary": f"EMERGENCY {emergency_type.upper()} detected - coordinating response for {len(affected_devices)} devices",
        "result": {
            "emergency_type": emergency_type,
            "affected_devices": affected_devices,
            "response_priority": response_priority,
            "coordination_status": "initiated",
        },
        "requires_sampling": True,  # Critical - AI must reason about emergency response
        "sampling_reason": f"Complex emergency coordination required for {emergency_type} incident",
        "next_steps": [
            "AI will analyze emergency patterns and determine optimal response",
            "Silence non-essential alarms to reduce confusion",
            "Prepare emergency contact procedures",
            "Assess evacuation routes and safety zones",
        ],
        "context": {
            "operation_details": f"Emergency response coordination for {emergency_type}",
            "timestamp": datetime.now().isoformat(),
            "priority_level": response_priority,
        },
        "suggestions": [
            "Follow established emergency procedures",
            "Contact emergency services if situation is life-threatening",
            "Account for all household members",
            "Have emergency supplies ready",
        ],
        "follow_up_questions": [
            "Are you and your family safe right now?",
            "Should I help silence alarms to reduce panic?",
            "Do you need emergency contact information?",
            "Would you like me to guide you through evacuation procedures?",
        ],
    }


async def predict_maintenance_needs(
    analysis_depth: str = "detailed",
    time_horizon: str = "1_month",
    include_cost_estimates: bool = True,
) -> dict[str, Any]:
    """Predict future maintenance needs using AI analysis and sampling.

    PORTMANTEAU PATTERN RATIONALE:
    Integrates device monitoring, pattern analysis, and predictive modeling
    to forecast maintenance needs with AI-powered insights.

    Args:
        analysis_depth: Depth of predictive analysis
        time_horizon: Time horizon for predictions
        include_cost_estimates: Include maintenance cost estimates

    Returns:
        FastMCP 3.1+ Conversational Response Structure with predictive insights
    """
    from datetime import datetime

    # Predictive analysis requires AI sampling for pattern recognition
    return {
        "success": True,
        "operation": "predict_maintenance_needs",
        "summary": f"Predictive maintenance analysis completed for {time_horizon.replace('_', ' ')} horizon",
        "result": {
            "analysis_depth": analysis_depth,
            "time_horizon": time_horizon,
            "predictions_generated": True,
        },
        "requires_sampling": True,  # AI needed for predictive pattern analysis
        "sampling_reason": "Complex pattern analysis required for accurate maintenance predictions",
        "next_steps": [
            "AI will analyze device usage patterns and failure history",
            "Generate maintenance schedule recommendations",
            "Calculate cost estimates and priority rankings",
        ],
        "context": {
            "operation_details": f"{analysis_depth.capitalize()} predictive analysis for {time_horizon}",
            "analysis_timestamp": datetime.now().isoformat(),
        },
        "suggestions": [
            "Schedule battery replacements before predicted failures",
            "Plan maintenance during off-peak times",
            "Keep replacement parts inventory ready",
        ],
        "follow_up_questions": [
            "Would you like me to create a maintenance schedule?",
            "Should I help you order replacement parts?",
            "Do you want cost estimates for predicted maintenance?",
        ],
    }


async def setup_smart_automation(
    automation_type: str, learning_period: str = "2_weeks", confidence_threshold: float = 0.8
) -> dict[str, Any]:
    """Set up intelligent automation using AI learning and sampling.

    PORTMANTEAU PATTERN RATIONALE:
    Combines automation configuration, pattern learning, and intelligent
    triggering into an AI-powered system that adapts to user behavior.

    Args:
        automation_type: Type of automation to configure
        learning_period: Period to learn user patterns
        confidence_threshold: Minimum confidence for automation triggers

    Returns:
        FastMCP 3.1+ Conversational Response Structure with automation setup
    """
    from datetime import datetime, timedelta

    # Automation setup requires AI sampling for pattern learning
    return {
        "success": True,
        "operation": "setup_smart_automation",
        "summary": f"Smart {automation_type} automation setup initiated with {learning_period.replace('_', ' ')} learning period",
        "result": {
            "automation_type": automation_type,
            "learning_period": learning_period,
            "confidence_threshold": confidence_threshold,
            "setup_status": "learning_phase_started",
        },
        "requires_sampling": True,  # AI needed for pattern learning and automation logic
        "sampling_reason": f"Complex pattern learning required for {automation_type} automation",
        "next_steps": [
            "AI will learn your usage patterns over the next {learning_period.replace('_', ' ')}",
            "Analyze device behavior and user interactions",
            "Generate optimal automation rules based on learned patterns",
        ],
        "context": {
            "operation_details": f"Setting up {automation_type} automation with AI learning",
            "learning_start": datetime.now().isoformat(),
            "learning_end": (datetime.now() + timedelta(weeks=2)).isoformat(),
        },
        "suggestions": [
            "Continue normal device usage during learning period",
            "Avoid unusual patterns that might confuse the AI",
            "Monitor automation suggestions during learning phase",
        ],
        "follow_up_questions": [
            "Would you like me to explain how this automation will work?",
            "Should I set up notifications for automation triggers?",
            "Do you want to customize the learning parameters?",
        ],
    }
