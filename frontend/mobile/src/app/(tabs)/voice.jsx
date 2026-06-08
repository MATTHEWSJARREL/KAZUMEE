import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { Mic, Send, Bot } from "lucide-react-native";

export default function VoiceScreen() {
  const insets = useSafeAreaInsets();
  const [command, setCommand] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSendCommand = async () => {
    if (!command.trim() || loading) return;

    const userMessage = command.trim();
    setCommand("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch("/api/voice-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: userMessage }),
      });

      if (!response.ok) throw new Error("Failed to send command");
      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't process that command. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: "white" }}>
      <StatusBar style="dark" />
      <View
        style={{ flex: 1, paddingTop: insets.top + 20, paddingHorizontal: 20 }}
      >
        {/* Header */}
        <View style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 28, fontWeight: "bold", marginBottom: 4 }}>
            Voice Commands
          </Text>
          <Text style={{ fontSize: 14, color: "#6B7280" }}>
            Control your stream with AI
          </Text>
        </View>

        {/* Messages */}
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
        >
          {messages.length === 0 && (
            <View style={{ alignItems: "center", paddingVertical: 48 }}>
              <Bot color="#D1D5DB" size={64} />
              <Text
                style={{
                  fontSize: 16,
                  fontWeight: "500",
                  color: "#6B7280",
                  marginTop: 12,
                }}
              >
                Kazumi AI Ready
              </Text>
              <Text
                style={{
                  fontSize: 14,
                  color: "#9CA3AF",
                  marginTop: 4,
                  textAlign: "center",
                }}
              >
                Try commands like "switch scene" or "create clip"
              </Text>
            </View>
          )}

          {messages.map((message, index) => (
            <View
              key={index}
              style={{
                marginBottom: 16,
                flexDirection: "row",
                alignItems: "flex-start",
                gap: 12,
              }}
            >
              {message.role === "assistant" && (
                <View
                  style={{
                    width: 32,
                    height: 32,
                    backgroundColor: "#8B5CF6",
                    borderRadius: 16,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Bot color="#fff" size={18} />
                </View>
              )}
              <View
                style={{
                  flex: 1,
                  backgroundColor: message.role === "user" ? "#000" : "#F3F4F6",
                  padding: 12,
                  borderRadius: 12,
                  marginLeft: message.role === "user" ? 40 : 0,
                }}
              >
                <Text
                  style={{
                    fontSize: 14,
                    color: message.role === "user" ? "#fff" : "#111",
                    lineHeight: 20,
                  }}
                >
                  {message.content}
                </Text>
              </View>
            </View>
          ))}

          {loading && (
            <View style={{ flexDirection: "row", gap: 12, marginBottom: 16 }}>
              <View
                style={{
                  width: 32,
                  height: 32,
                  backgroundColor: "#8B5CF6",
                  borderRadius: 16,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Bot color="#fff" size={18} />
              </View>
              <View
                style={{
                  backgroundColor: "#F3F4F6",
                  padding: 12,
                  borderRadius: 12,
                }}
              >
                <ActivityIndicator size="small" color="#000" />
              </View>
            </View>
          )}
        </ScrollView>

        {/* Input */}
        <View
          style={{
            flexDirection: "row",
            gap: 12,
            paddingBottom: insets.bottom + 20,
            paddingTop: 12,
            borderTopWidth: 1,
            borderTopColor: "#E5E7EB",
          }}
        >
          <TextInput
            value={command}
            onChangeText={setCommand}
            placeholder="Enter voice command..."
            style={{
              flex: 1,
              backgroundColor: "#F9FAFB",
              paddingHorizontal: 16,
              paddingVertical: 12,
              borderRadius: 24,
              fontSize: 14,
            }}
            multiline
          />
          <TouchableOpacity
            onPress={handleSendCommand}
            disabled={!command.trim() || loading}
            style={{
              width: 48,
              height: 48,
              backgroundColor: command.trim() && !loading ? "#000" : "#E5E7EB",
              borderRadius: 24,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Send
              color={command.trim() && !loading ? "#fff" : "#9CA3AF"}
              size={20}
            />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
