import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { analyze_photo } from "../utility";

interface AnalyzeResult {
  fridge_items?: Record<string, boolean> | string;
  overlapping_ads?: any;
  metrics?: {
    duration_seconds?: number;
    payload_chars?: number;
  };
}

export default function AnalyzerScreen() {
  const [asset, setAsset] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ensurePermissions() {
    const mediaPermission = await ImagePicker.getMediaLibraryPermissionsAsync();
    if (mediaPermission.granted) return true;
    const request = await ImagePicker.requestMediaLibraryPermissionsAsync();
    return request.granted;
  }

  async function handlePickImage() {
    setError(null);
    const granted = await ensurePermissions();
    if (!granted) {
      setError("Permission to access the photo library is required.");
      return;
    }

    const pickerResult = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsMultipleSelection: false,
    });

    if (pickerResult.canceled || !pickerResult.assets.length) {
      return;
    }

    setAsset(pickerResult.assets[0]);
    setResult(null);
  }

  async function handleAnalyze() {
    if (!asset) {
      setError("Select an image before analyzing.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const analysis = await analyze_photo(asset);
      setResult(analysis);
    } catch (err: any) {
      setError(err.message ?? "Failed to analyze image.");
    } finally {
      setLoading(false);
    }
  }

  function renderFridgeItems(items: AnalyzeResult["fridge_items"]) {
    if (!items) return <ThemedText>No refrigerator items detected.</ThemedText>;
    if (typeof items === "string") {
      return <ThemedText>{items}</ThemedText>;
    }

    const entries = Object.entries(items);
    if (!entries.length) {
      return <ThemedText>No refrigerator items detected.</ThemedText>;
    }

    return entries.map(([item, perishable]) => (
      <View key={item} style={styles.resultRow}>
        <Text style={styles.resultItem}>{item}</Text>
        <Text style={styles.resultTag}>{perishable ? "Perishable" : "Shelf-stable"}</Text>
      </View>
    ));
  }

  function renderOverlaps(payload: AnalyzeResult["overlapping_ads"]) {
    if (!payload) {
      return <ThemedText>No overlapping weekly ads returned.</ThemedText>;
    }

    if (typeof payload === "string") {
      return <ThemedText>{payload}</ThemedText>;
    }

    if (!Array.isArray(payload) || !payload.length) {
      return <ThemedText>No overlapping weekly ads returned.</ThemedText>;
    }

    return payload.map((entry, idx) => {
      if (!entry) return null;
      const { item_name, perishable, product, price } = entry;
      return (
        <View key={`${item_name || idx}-${idx}`} style={styles.overlapCard}>
          <Text style={styles.overlapTitle}>{item_name || entry.product || "Item"}</Text>
          {typeof perishable !== "undefined" && (
            <Text style={styles.overlapMeta}>{perishable ? "Perishable" : "Shelf-stable"}</Text>
          )}
          {product && <Text style={styles.overlapMeta}>Ad match: {product}</Text>}
          {price && <Text style={styles.overlapMeta}>Price: {price}</Text>}
        </View>
      );
    });
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <ThemedText type="title">Analyze a Fridge Photo</ThemedText>
        <ThemedText style={styles.subtitle}>
          Upload a refrigerator photo to identify items and automatically match weekly ad deals.
        </ThemedText>

        <View style={styles.actions}>
          <Button title="Choose Photo" onPress={handlePickImage} />
          <Button
            title={loading ? "Analyzing..." : "Analyze Photo"}
            onPress={handleAnalyze}
            disabled={!asset || loading}
            color={!asset || loading ? "#999" : undefined}
          />
        </View>

        {asset && (
          <View style={styles.previewCard}>
            <Image source={{ uri: asset.uri }} style={styles.previewImage} contentFit="cover" />
            <Text style={styles.previewLabel}>{asset.fileName ?? "Selected photo"}</Text>
          </View>
        )}

        {loading && <ActivityIndicator style={styles.loader} />}
        {error && <ThemedText style={styles.errorText}>{error}</ThemedText>}

        {result && (
          <View style={styles.resultsCard}>
            <ThemedText type="subtitle">Detected Refrigerator Items</ThemedText>
            {renderFridgeItems(result.fridge_items)}

            <ThemedText type="subtitle" style={styles.sectionSpacer}>
              Weekly Ad Matches
            </ThemedText>
            {renderOverlaps(result.overlapping_ads)}

            {result.metrics && (
              <View style={styles.metricsRow}>
                {typeof result.metrics.duration_seconds === "number" && (
                  <Text style={styles.metricChip}>
                    {result.metrics.duration_seconds.toFixed(1)}s processing
                  </Text>
                )}
                {typeof result.metrics.payload_chars === "number" && (
                  <Text style={styles.metricChip}>{result.metrics.payload_chars} chars uploaded</Text>
                )}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    padding: 16,
    gap: 16,
  },
  subtitle: {
    marginTop: 4,
    color: "#555",
  },
  actions: {
    flexDirection: "row",
    gap: 12,
    flexWrap: "wrap",
    alignItems: "center",
  },
  previewCard: {
    borderRadius: 12,
    backgroundColor: "#f2f2f2",
    padding: 12,
    alignItems: "center",
    gap: 8,
  },
  previewImage: {
    width: "100%",
    borderRadius: 12,
    aspectRatio: 4 / 3,
  },
  previewLabel: {
    fontSize: 14,
    color: "#444",
  },
  loader: {
    marginTop: 8,
  },
  errorText: {
    color: "#cc0033",
  },
  resultsCard: {
    borderRadius: 14,
    backgroundColor: "#fff",
    padding: 16,
    gap: 12,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  resultRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#e0e0e0",
  },
  resultItem: {
    fontWeight: "600",
    color: "#222",
  },
  resultTag: {
    color: "#0f6b2f",
    fontWeight: "500",
  },
  sectionSpacer: {
    marginTop: 16,
  },
  overlapCard: {
    borderWidth: 1,
    borderColor: "#e4e4e4",
    borderRadius: 10,
    padding: 10,
    marginTop: 8,
    backgroundColor: "#fafafa",
  },
  overlapTitle: {
    fontWeight: "600",
    fontSize: 16,
  },
  overlapMeta: {
    color: "#555",
    marginTop: 4,
  },
  metricsRow: {
    flexDirection: "row",
    gap: 8,
    flexWrap: "wrap",
    marginTop: 12,
  },
  metricChip: {
    backgroundColor: "#eef2ff",
    color: "#1f3bb3",
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 999,
    fontSize: 12,
  },
});
