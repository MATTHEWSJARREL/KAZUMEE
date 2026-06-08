import { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import {
  Eye,
  Activity,
  Scissors,
  Shield,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Zap,
} from "lucide-react-native";

export default function DashboardScreen() {
  const insets = useSafeAreaInsets();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await fetch("/api/dashboard");
      if (!response.ok) throw new Error("Failed to fetch");
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const StatCard = ({ icon: Icon, label, value, delta, color }) => (
    <View
      style={{
        backgroundColor: "white",
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: "#E5E7EB",
        marginBottom: 12,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <View
          style={{
            width: 48,
            height: 48,
            backgroundColor: `${color}20`,
            borderRadius: 24,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon color={color} size={24} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, color: "#6B7280", marginBottom: 4 }}>
            {label}
          </Text>
          <Text style={{ fontSize: 24, fontWeight: "bold" }}>{value}</Text>
          {delta && (
            <Text style={{ fontSize: 12, color: "#10B981", marginTop: 2 }}>
              {delta}
            </Text>
          )}
        </View>
      </View>
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
        <Text style={{ marginTop: 12, color: "#6B7280" }}>Loading...</Text>
        <StatusBar style="dark" />
      </View>
    );
  }

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
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={{ marginBottom: 24 }}>
          <Text style={{ fontSize: 28, fontWeight: "bold", marginBottom: 4 }}>
            Kazumi Dashboard
          </Text>
          <Text style={{ fontSize: 14, color: "#6B7280" }}>
            Adaptive AI Streaming Assistant
          </Text>
        </View>

        {/* AI Status */}
        <View
          style={{
            backgroundColor: "#10B98120",
            padding: 16,
            borderRadius: 12,
            flexDirection: "row",
            alignItems: "center",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <Zap color="#10B981" size={20} fill="#10B981" />
          <View style={{ flex: 1 }}>
            <Text style={{ fontWeight: "bold", fontSize: 14 }}>
              AI Learning Active
            </Text>
            <Text style={{ fontSize: 12, color: "#6B7280" }}>
              {data?.mlConfidence || 0}% confidence
            </Text>
          </View>
        </View>

        {/* Stats */}
        <StatCard
          icon={Eye}
          label="Current Viewers"
          value={data?.currentViewers || 0}
          delta={data?.viewerChange}
          color="#3B82F6"
        />
        <StatCard
          icon={Activity}
          label="Stream Health"
          value={data?.healthStatus || "Healthy"}
          delta={`${data?.healthScore || 0}% score`}
          color="#10B981"
        />
        <StatCard
          icon={Scissors}
          label="Auto Clips Today"
          value={data?.autoClips || 0}
          delta={`${data?.manualClips || 0} manual`}
          color="#8B5CF6"
        />
        <StatCard
          icon={Shield}
          label="Mod Events"
          value={data?.modEvents || 0}
          delta={`${data?.autoModerated || 0}% auto`}
          color="#F59E0B"
        />

        {/* Recent Activity */}
        <View style={{ marginTop: 12 }}>
          <Text style={{ fontSize: 18, fontWeight: "bold", marginBottom: 12 }}>
            Recent Activity
          </Text>
          {(data?.recentActivity || []).slice(0, 5).map((activity, index) => (
            <View
              key={index}
              style={{
                backgroundColor: "white",
                padding: 12,
                borderRadius: 8,
                borderWidth: 1,
                borderColor: "#E5E7EB",
                marginBottom: 8,
                flexDirection: "row",
                alignItems: "center",
                gap: 12,
              }}
            >
              {activity.status === "completed" ? (
                <CheckCircle color="#10B981" size={16} />
              ) : (
                <AlertCircle color="#F59E0B" size={16} />
              )}
              <View style={{ flex: 1 }}>
                <Text
                  style={{ fontSize: 13, fontWeight: "500", marginBottom: 2 }}
                >
                  {activity.description}
                </Text>
                <Text style={{ fontSize: 11, color: "#6B7280" }}>
                  {activity.time}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}
