import { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import {
  Cpu,
  Activity,
  HardDrive,
  Wifi,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from "lucide-react-native";

export default function HealthScreen() {
  const insets = useSafeAreaInsets();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      const response = await fetch("/api/stream-health");
      if (!response.ok) throw new Error("Failed to fetch");
      const result = await response.json();
      setHealth(result);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const MetricCard = ({ icon: Icon, label, value, unit, isWarning }) => (
    <View
      style={{
        backgroundColor: isWarning ? "#FEF3C7" : "white",
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: isWarning ? "#F59E0B" : "#E5E7EB",
      }}
    >
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <Icon color={isWarning ? "#F59E0B" : "#6B7280"} size={20} />
        {isWarning && <AlertTriangle color="#F59E0B" size={16} />}
      </View>
      <Text style={{ fontSize: 12, color: "#6B7280", marginBottom: 4 }}>
        {label}
      </Text>
      <Text style={{ fontSize: 28, fontWeight: "bold" }}>
        {value}
        <Text style={{ fontSize: 16, color: "#6B7280" }}>{unit}</Text>
      </Text>
    </View>
  );

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: "white",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <ActivityIndicator size="large" color="#000" />
        <Text style={{ marginTop: 12, color: "#6B7280" }}>
          Loading health data...
        </Text>
        <StatusBar style="dark" />
      </View>
    );
  }

  const isHealthy = health?.healthStatus === "healthy";

  return (
    <View style={{ flex: 1, backgroundColor: "white" }}>
      <StatusBar style="dark" />
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{
          paddingTop: insets.top + 20,
          paddingBottom: insets.bottom + 20,
          paddingHorizontal: 20,
        }}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 24,
          }}
        >
          <View>
            <Text style={{ fontSize: 28, fontWeight: "bold", marginBottom: 4 }}>
              Stream Health
            </Text>
            <Text style={{ fontSize: 14, color: "#6B7280" }}>
              Real-time monitoring
            </Text>
          </View>
          <TouchableOpacity onPress={fetchHealth}>
            <RefreshCw color="#000" size={24} />
          </TouchableOpacity>
        </View>

        {/* Overall Status */}
        <View
          style={{
            backgroundColor: isHealthy ? "#10B98120" : "#FEF3C7",
            padding: 20,
            borderRadius: 12,
            flexDirection: "row",
            alignItems: "center",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <View
            style={{
              width: 56,
              height: 56,
              backgroundColor: "white",
              borderRadius: 28,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {isHealthy ? (
              <CheckCircle color="#10B981" size={32} />
            ) : (
              <AlertTriangle color="#F59E0B" size={32} />
            )}
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, color: "#6B7280", marginBottom: 4 }}>
              Overall Status
            </Text>
            <Text
              style={{
                fontSize: 24,
                fontWeight: "bold",
                textTransform: "capitalize",
              }}
            >
              {health?.healthStatus || "Unknown"}
            </Text>
          </View>
        </View>

        {/* Metrics Grid */}
        <View style={{ gap: 12 }}>
          <View style={{ flexDirection: "row", gap: 12 }}>
            <View style={{ flex: 1 }}>
              <MetricCard
                icon={Cpu}
                label="CPU Usage"
                value={health?.cpuUsage || 0}
                unit="%"
                isWarning={(health?.cpuUsage || 0) > 80}
              />
            </View>
            <View style={{ flex: 1 }}>
              <MetricCard
                icon={Activity}
                label="GPU Usage"
                value={health?.gpuUsage || 0}
                unit="%"
                isWarning={(health?.gpuUsage || 0) > 90}
              />
            </View>
          </View>

          <View style={{ flexDirection: "row", gap: 12 }}>
            <View style={{ flex: 1 }}>
              <MetricCard
                icon={HardDrive}
                label="Memory"
                value={health?.memoryUsage || 0}
                unit="%"
                isWarning={(health?.memoryUsage || 0) > 85}
              />
            </View>
            <View style={{ flex: 1 }}>
              <MetricCard
                icon={Wifi}
                label="Latency"
                value={health?.networkLatency || 0}
                unit="ms"
                isWarning={(health?.networkLatency || 0) > 50}
              />
            </View>
          </View>
        </View>

        {/* AI Predictions */}
        <View style={{ marginTop: 24 }}>
          <Text style={{ fontSize: 18, fontWeight: "bold", marginBottom: 12 }}>
            AI Predictions
          </Text>
          {(health?.predictions || []).map((prediction, index) => (
            <View
              key={index}
              style={{
                backgroundColor: "#F9FAFB",
                padding: 12,
                borderRadius: 8,
                marginBottom: 8,
                flexDirection: "row",
                gap: 12,
              }}
            >
              <View
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  backgroundColor:
                    prediction.severity === "high"
                      ? "#EF4444"
                      : prediction.severity === "medium"
                        ? "#F59E0B"
                        : "#10B981",
                  marginTop: 4,
                }}
              />
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, marginBottom: 4 }}>
                  {prediction.message}
                </Text>
                <Text style={{ fontSize: 11, color: "#6B7280" }}>
                  {prediction.confidence}% confidence
                </Text>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}
