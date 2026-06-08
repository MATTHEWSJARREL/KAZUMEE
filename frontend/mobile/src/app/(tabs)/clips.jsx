import { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { Scissors, Sparkles, Play, Eye, Plus } from "lucide-react-native";

export default function ClipsScreen() {
  const insets = useSafeAreaInsets();
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchClips();
  }, [filter]);

  const fetchClips = async () => {
    try {
      const response = await fetch(`/api/clips?filter=${filter}`);
      if (!response.ok) throw new Error("Failed to fetch");
      const result = await response.json();
      setClips(result.clips || []);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const FilterButton = ({ value, label }) => (
    <TouchableOpacity
      onPress={() => setFilter(value)}
      style={{
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 8,
        backgroundColor: filter === value ? "#000" : "#F3F4F6",
      }}
    >
      <Text
        style={{
          fontSize: 14,
          fontWeight: "500",
          color: filter === value ? "#fff" : "#6B7280",
        }}
      >
        {label}
      </Text>
    </TouchableOpacity>
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
          Loading clips...
        </Text>
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
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <View>
            <Text style={{ fontSize: 28, fontWeight: "bold", marginBottom: 4 }}>
              Clips Library
            </Text>
            <Text style={{ fontSize: 14, color: "#6B7280" }}>
              {clips.length} total clips
            </Text>
          </View>
          <TouchableOpacity
            style={{
              width: 44,
              height: 44,
              backgroundColor: "#000",
              borderRadius: 22,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Plus color="#fff" size={24} />
          </TouchableOpacity>
        </View>

        {/* Filters */}
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 20 }}>
          <FilterButton value="all" label="All" />
          <FilterButton value="auto" label="Auto" />
          <FilterButton value="manual" label="Manual" />
        </View>

        {/* Clips List */}
        {clips.map((clip, index) => (
          <TouchableOpacity
            key={index}
            style={{
              backgroundColor: "white",
              borderRadius: 12,
              borderWidth: 1,
              borderColor: "#E5E7EB",
              marginBottom: 12,
              overflow: "hidden",
            }}
          >
            {/* Thumbnail */}
            <View
              style={{
                backgroundColor: "#1F2937",
                aspectRatio: 16 / 9,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Play color="#fff" size={32} opacity={0.75} />
              {clip.auto_detected && (
                <View
                  style={{
                    position: "absolute",
                    top: 8,
                    right: 8,
                    backgroundColor: "#8B5CF6",
                    paddingHorizontal: 8,
                    paddingVertical: 4,
                    borderRadius: 4,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <Sparkles color="#fff" size={12} />
                  <Text
                    style={{ color: "#fff", fontSize: 10, fontWeight: "bold" }}
                  >
                    AUTO
                  </Text>
                </View>
              )}
              <View
                style={{
                  position: "absolute",
                  bottom: 8,
                  right: 8,
                  backgroundColor: "rgba(0,0,0,0.75)",
                  paddingHorizontal: 6,
                  paddingVertical: 2,
                  borderRadius: 4,
                }}
              >
                <Text style={{ color: "#fff", fontSize: 10 }}>
                  {clip.timestamp_end - clip.timestamp_start}s
                </Text>
              </View>
            </View>

            {/* Info */}
            <View style={{ padding: 12 }}>
              <Text
                style={{ fontSize: 16, fontWeight: "bold", marginBottom: 4 }}
              >
                {clip.title}
              </Text>
              {clip.description && (
                <Text
                  style={{ fontSize: 13, color: "#6B7280", marginBottom: 8 }}
                  numberOfLines={2}
                >
                  {clip.description}
                </Text>
              )}

              {/* Tags */}
              {clip.tags && clip.tags.length > 0 && (
                <View
                  style={{
                    flexDirection: "row",
                    flexWrap: "wrap",
                    gap: 6,
                    marginBottom: 8,
                  }}
                >
                  {clip.tags.slice(0, 3).map((tag, i) => (
                    <View
                      key={i}
                      style={{
                        backgroundColor: "#F3F4F6",
                        paddingHorizontal: 8,
                        paddingVertical: 4,
                        borderRadius: 4,
                      }}
                    >
                      <Text style={{ fontSize: 11, color: "#6B7280" }}>
                        #{tag}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Stats */}
              <View
                style={{ flexDirection: "row", alignItems: "center", gap: 12 }}
              >
                <View
                  style={{ flexDirection: "row", alignItems: "center", gap: 4 }}
                >
                  <Eye color="#6B7280" size={14} />
                  <Text style={{ fontSize: 12, color: "#6B7280" }}>
                    {clip.view_count || 0}
                  </Text>
                </View>
                {clip.performance_score && (
                  <View
                    style={{
                      flexDirection: "row",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <Scissors color="#6B7280" size={14} />
                    <Text style={{ fontSize: 12, color: "#6B7280" }}>
                      {Math.round(clip.performance_score * 100)}%
                    </Text>
                  </View>
                )}
              </View>
            </View>
          </TouchableOpacity>
        ))}

        {clips.length === 0 && (
          <View style={{ alignItems: "center", paddingVertical: 48 }}>
            <Scissors color="#D1D5DB" size={48} />
            <Text
              style={{
                fontSize: 16,
                fontWeight: "500",
                color: "#6B7280",
                marginTop: 12,
              }}
            >
              No clips found
            </Text>
            <Text style={{ fontSize: 14, color: "#9CA3AF", marginTop: 4 }}>
              Start streaming to detect highlights
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}
