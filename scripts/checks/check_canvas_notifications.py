#!/usr/bin/env python3
"""
Script to check Canvas notifications and communication settings.
"""

import sys
from pathlib import Path

import requests

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
import src.canvas_mcp.config as config


def main():
    """Main function to check Canvas notifications."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Check notification preferences
        print("\nChecking notification preferences...")
        try:
            # Direct API call since canvasapi doesn't have this method
            url = f"{config.API_URL}/users/self/communication_channels"
            headers = {"Authorization": f"Bearer {config.API_KEY}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                channels = response.json()
                print(f"Found {len(channels)} communication channels")
                for i, channel in enumerate(channels):
                    print(f"\nChannel {i + 1}: {channel.get('type', 'Unknown type')}")
                    print(f"- Address: {channel.get('address', 'No address')}")
                    print(f"- Position: {channel.get('position', 'Unknown')}")
                    print(
                        f"- Active: {channel.get('workflow_state', 'Unknown') == 'active'}"
                    )

                    # Check notification preferences for this channel
                    channel_id = channel.get("id")
                    if channel_id:
                        pref_url = f"{config.API_URL}/users/self/communication_channels/{channel_id}/notification_preferences"
                        pref_response = requests.get(pref_url, headers=headers)
                        if pref_response.status_code == 200:
                            prefs = pref_response.json().get(
                                "notification_preferences", {}
                            )
                            print("- Notification preferences:")

                            # Check announcement preferences specifically
                            announcement_prefs = {
                                k: v
                                for k, v in prefs.items()
                                if "announcement" in k.lower()
                            }
                            for pref_name, pref_data in announcement_prefs.items():
                                print(
                                    f"  - {pref_name}: {pref_data.get('frequency', 'Unknown')}"
                                )
                        else:
                            print(
                                f"- Error getting preferences: {pref_response.status_code}"
                            )
            else:
                print(f"Error: Status code {response.status_code}")
                print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error checking notification preferences: {e}")

        # Check IDS 385 course specifically
        course_id = 65920000000145100  # IDS 385
        print(f"\nChecking IDS 385 course (ID: {course_id})...")

        try:
            course = canvas_api_client.get_course(course_id)
            print(f"Course: {course.name} ({course.course_code})")

            # Check course settings
            print("\nCourse settings:")
            for attr in dir(course):
                if not attr.startswith("_") and not callable(getattr(course, attr)):
                    value = getattr(course, attr)
                    if isinstance(value, str | int | bool | float) or value is None:
                        print(f"- {attr}: {value}")

            # Check course features
            print("\nChecking course features...")
            try:
                url = f"{config.API_URL}/courses/{course_id}/features"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    features = response.json()
                    print(f"Found {len(features)} features:")
                    for feature in features:
                        print(
                            f"- {feature.get('feature', 'Unknown')}: {feature.get('state', 'Unknown')}"
                        )
                else:
                    print(f"Error: Status code {response.status_code}")
            except Exception as e:
                print(f"Error checking course features: {e}")

            # Check tabs (navigation items)
            print("\nChecking course tabs...")
            try:
                tabs = course.get_tabs()
                print(f"Found {len(tabs)} tabs:")
                for tab in tabs:
                    print(
                        f"- {tab.label} (ID: {tab.id}, Visible: {getattr(tab, 'visibility', 'Unknown')})"
                    )
            except Exception as e:
                print(f"Error checking tabs: {e}")

        except Exception as e:
            print(f"Error checking IDS 385 course: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
