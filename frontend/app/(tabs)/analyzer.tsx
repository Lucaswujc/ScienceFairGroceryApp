import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import React, { useMemo, useState } from "react";
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
import { useBasket } from "@/context/BasketContext";
import type { Ad } from "@/types/ad";
import { analyze_photo } from "../utility";

interface AnalyzeResult {
  fridge_items?: Record<string, boolean> | string;
  overlapping_ads?: any;
  metrics?: {
    duration_seconds?: number;
    payload_chars?: number;
  };
}

type NormalizedOverlap = {
  ad: Ad;
  perishable?: boolean;
};

function getAdKey(item: Ad) {
  return [
    item.product?.toLowerCase() ?? "",
    item.store?.toLowerCase() ?? "",
    String(item.price ?? ""),
    item.date ?? "",
    item.image_filename ?? "",
  ].join("|");
}

function normalizeOverlapEntry(entry: any): NormalizedOverlap | null {
  if (!entry) {
    return null;
  }

  const rawProduct =
    entry.product ??
    entry.item_name ??
    entry.name ??
    entry.title ??
    entry.description;
  const product =
    typeof rawProduct === "string"
      ? rawProduct.trim()
      : typeof rawProduct === "number"
      ? String(rawProduct)
      : "";
  if (!product) {
    return null;
  }

  const rawPrice =
    entry.price ??
    entry.sale_price ??
    entry.offer_price ??
    entry.deal_price ??
    entry.cost;

  let price: string | number = "";
  if (typeof rawPrice === "number" || typeof rawPrice === "string") {
    price = rawPrice;
  } else if (rawPrice !== undefined && rawPrice !== null) {
    price = String(rawPrice);
  }

  const imageUri =
    typeof entry.image_uri === "string"
      ? entry.image_uri
      : typeof entry.image_url === "string"
      ? entry.image_url
      : undefined;

  const ad: Ad = {
    product,
    price,
    store:
      typeof entry.store === "string"
        ? entry.store
        : typeof entry.store_name === "string"
        ? entry.store_name
        : typeof entry.retailer === "string"
        ? entry.retailer
        : undefined,
    date:
      typeof entry.date === "string"
        ? entry.date
        : typeof entry.sale_date === "string"
        ? entry.sale_date
        : undefined,
    image_base64:
      typeof entry.image_base64 === "string"
        ? entry.image_base64
        : undefined,
    image_uri: imageUri,
    image_filename:
      typeof entry.image_filename === "string"
        ? entry.image_filename
        : undefined,
  };

  return {
    ad,
    perishable:
      typeof entry.perishable === "boolean" ? entry.perishable : undefined,
  };
}

function normalizeOverlapEntries(
  payload: AnalyzeResult["overlapping_ads"]
): NormalizedOverlap[] {
  if (!Array.isArray(payload)) {
    return [];
  }

  const seen = new Set<string>();
  const normalized: NormalizedOverlap[] = [];

  payload.forEach((entry) => {
    const normalizedEntry = normalizeOverlapEntry(entry);
    if (!normalizedEntry) {
      return;
    }
    const key = getAdKey(normalizedEntry.ad);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    normalized.push(normalizedEntry);
  });

  return normalized;
}

export default function AnalyzerScreen() {
  const [asset, setAsset] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addToBasket, isInBasket } = useBasket();

  const normalizedOverlaps = useMemo(
    () => normalizeOverlapEntries(result?.overlapping_ads),
    [result?.overlapping_ads]
  );

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

  function renderOverlaps(
    payload: AnalyzeResult["overlapping_ads"],
    normalized: NormalizedOverlap[]
  ) {
    if (!payload) {
      return <ThemedText>No overlapping weekly ads returned.</ThemedText>;
    }

    if (typeof payload === "string") {
      return <ThemedText>{payload}</ThemedText>;
    }

    if (!Array.isArray(payload) || !payload.length || !normalized.length) {
      return <ThemedText>No overlapping weekly ads returned.</ThemedText>;
    }

    return normalized.map(({ ad, perishable }, idx) => {
      const inBasket = isInBasket(ad);
      const hasPrice = ad.price !== undefined && ad.price !== null && ad.price !== "";

      return (
        <View key={`${getAdKey(ad)}-${idx}`} style={styles.overlapCard}>
          <Text style={styles.overlapTitle}>{ad.product}</Text>
          {typeof perishable !== "undefined" && (
            <Text style={styles.overlapMeta}>
              {perishable ? "Perishable" : "Shelf-stable"}
            </Text>
          )}
          {ad.store && <Text style={styles.overlapMeta}>Store: {ad.store}</Text>}
          {ad.date && <Text style={styles.overlapMeta}>Ad date: {ad.date}</Text>}
          {hasPrice && (
            <Text style={styles.overlapPrice}>Price: {String(ad.price)}</Text>
          )}
          <View style={styles.overlapActions}>
            <Button
              title={inBasket ? "In Cart" : "Add to Cart"}
              onPress={() => addToBasket(ad)}
              disabled={inBasket}
              color={inBasket ? "#999" : undefined}
            />
          </View>
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
            {renderOverlaps(result.overlapping_ads, normalizedOverlaps)}

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
  overlapPrice: {
    color: "#1f3bb3",
    marginTop: 6,
    fontWeight: "600",
  },
  overlapActions: {
    marginTop: 10,
    alignItems: "flex-start",
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
