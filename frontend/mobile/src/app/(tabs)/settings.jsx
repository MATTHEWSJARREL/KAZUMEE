import { View, Text, ScrollView, TouchableOpacity, Switch } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import {
  User,
  Mic,
  Shield,
  Zap,
  Bell,
  ChevronRight,
} from "lucide-react-native";

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();

  const SettingItem = ({
    icon: Icon,
    label,
    value,
    onPress,
    showArrow = true,
  }) => (
    <TouchableOpacity
      onPress={onPress}
      style={{
        flexDirection: "row",
        alignItems: "center",
        padding: 16,
        backgroundColor: "white",
        borderBottomWidth: 1,
        borderBottomColor: "#E5E7EB",
      }}
    >
      <Icon color="#6B7280" size={20} />
      <Text style={{ flex: 1, fontSize: 15, marginLeft: 12 }}>{label}</Text>
      {value && (
        <Text style={{ fontSize: 14, color: "#6B7280", marginRight: 8 }}>
          {value}
        </Text>
      )}
      {showArrow && <ChevronRight color="#9CA3AF" size={20} />}
    </TouchableOpacity>
  );

  const SettingToggle = ({ icon: Icon, label, value, onValueChange }) => (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        padding: 16,
        backgroundColor: "white",
        borderBottomWidth: 1,
        borderBottomColor: "#E5E7EB",
      }}
    >
      <Icon color="#6B7280" size={20} />
      <Text style={{ flex: 1, fontSize: 15, marginLeft: 12 }}>{label}</Text>
      <Switch value={value} onValueChange={onValueChange} />
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: "#F9FAFB" }}>
      <StatusBar style="dark" />
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{
          paddingTop: insets.top + 20,
          paddingBottom: insets.bottom + 20,
        }}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={{ paddingHorizontal: 20, marginBottom: 24 }}>
          <Text style={{ fontSize: 28, fontWeight: "bold", marginBottom: 4 }}>
            Settings
          </Text>
          <Text style={{ fontSize: 14, color: "#6B7280" }}>
            Configure Kazumi AI
          </Text>
        </View>

        {/* Profile Section */}
        <View style={{ marginBottom: 24 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "600",
              color: "#6B7280",
              paddingHorizontal: 20,
              marginBottom: 8,
            }}
          >
            PROFILE
          </Text>
          <SettingItem
            icon={User}
            label="Display Name"
            value="KazumiPro"
            onPress={() => {}}
          />
          <SettingItem
            icon={User}
            label="Account Settings"
            onPress={() => {}}
          />
        </View>

        {/* Voice Section */}
        <View style={{ marginBottom: 24 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "600",
              color: "#6B7280",
              paddingHorizontal: 20,
              marginBottom: 8,
            }}
          >
            VOICE
          </Text>
          <SettingItem
            icon={Mic}
            label="Voice Model"
            value="Standard"
            onPress={() => {}}
          />
          <SettingToggle
            icon={Mic}
            label="Voice Commands"
            value={true}
            onValueChange={() => {}}
          />
        </View>

        {/* Moderation Section */}
        <View style={{ marginBottom: 24 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "600",
              color: "#6B7280",
              paddingHorizontal: 20,
              marginBottom: 8,
            }}
          >
            MODERATION
          </Text>
          <SettingItem
            icon={Shield}
            label="Strictness Level"
            value="Medium"
            onPress={() => {}}
          />
          <SettingToggle
            icon={Shield}
            label="Auto-Moderation"
            value={true}
            onValueChange={() => {}}
          />
        </View>

        {/* Automation Section */}
        <View style={{ marginBottom: 24 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "600",
              color: "#6B7280",
              paddingHorizontal: 20,
              marginBottom: 8,
            }}
          >
            AUTOMATION
          </Text>
          <SettingToggle
            icon={Zap}
            label="Auto-Generate Clips"
            value={true}
            onValueChange={() => {}}
          />
          <SettingToggle
            icon={Zap}
            label="Auto-Create Highlights"
            value={true}
            onValueChange={() => {}}
          />
          <SettingToggle
            icon={Zap}
            label="Scene Auto-Switching"
            value={false}
            onValueChange={() => {}}
          />
        </View>

        {/* Notifications Section */}
        <View style={{ marginBottom: 24 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "600",
              color: "#6B7280",
              paddingHorizontal: 20,
              marginBottom: 8,
            }}
          >
            NOTIFICATIONS
          </Text>
          <SettingToggle
            icon={Bell}
            label="Stream Health Alerts"
            value={true}
            onValueChange={() => {}}
          />
          <SettingToggle
            icon={Bell}
            label="Moderation Alerts"
            value={true}
            onValueChange={() => {}}
          />
          <SettingToggle
            icon={Bell}
            label="Clip Detections"
            value={true}
            onValueChange={() => {}}
          />
        </View>

        {/* Version */}
        <View style={{ paddingHorizontal: 20, paddingVertical: 24 }}>
          <Text style={{ fontSize: 12, color: "#9CA3AF", textAlign: "center" }}>
            Kazumi AI v1.0.0
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}
