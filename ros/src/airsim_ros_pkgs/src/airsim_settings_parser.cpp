#include "airsim_settings_parser.h"

AirSimSettingsParser::AirSimSettingsParser(const std::string& host_ip)
    : host_ip_(host_ip)
{
    success_ = initializeSettings();
}

bool AirSimSettingsParser::success()
{
    return success_;
}

bool AirSimSettingsParser::getSettingsText(std::string& settings_text) const
{
    while (true) {
        msr::airlib::RpcLibClientBase airsim_client(host_ip_);
        std::this_thread::sleep_for(std::chrono::seconds(1));
        if (airsim_client.getConnectionState() == msr::airlib::RpcLibClientBase::ConnectionState::Connected) {
            settings_text = airsim_client.getSettingsString();
            return !settings_text.empty();
            // break;
        }
        else {
            std::cout << "Failed to connect to Airsim server! Try to reconnect..." << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    // airsim_client.confirmConnection();


}

std::string AirSimSettingsParser::getSimMode()
{
    const auto& settings_json = msr::airlib::Settings::loadJSonString(settings_text_);
    return settings_json.getString("SimMode", "");
}

// mimics void ASimHUD::initializeSettings()
bool AirSimSettingsParser::initializeSettings()
{
    if (getSettingsText(settings_text_)) {
        AirSimSettings::initializeSettings(settings_text_);

        AirSimSettings::singleton().load(std::bind(&AirSimSettingsParser::getSimMode, this));
        std::cout << "SimMode: " << AirSimSettings::singleton().simmode_name << std::endl;

        return true;
    }

    return false;
}
