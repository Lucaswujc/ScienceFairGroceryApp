import { Image } from "expo-image";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Button,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { get_image, get_store_ads } from "../utility";

type Ad = {
  product: string;
  price: string | number;
  image_base64?: string | null;
  image_uri?: string | null;
  image_filename?: string | null;
  store?: string;
  date?: string; // YYYY-MM-DD
};

const KNOWN_STORES = ["HEB", "Kroger", "Tom Thumb"];

export default function AdsScreen() {
  const [storeFilter, setStoreFilter] = useState<"All" | string>("All");
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState(""); // optional local filter
  const [basket, setBasket] = useState<Ad[]>([]);

  useEffect(() => {
    fetchAdsForSelection();
  }, [storeFilter]);

  async function fetchAdsForSelection() {
    setLoading(true);
    setError(null);
    try {
      // Determine week value to send to API. If no dateFilter, use current week's Monday
      let week: string;
      week = dateFilter || getMondayISO(new Date());
      let results: Ad[] = [];
      const storesToQuery =
        storeFilter === "All" ? KNOWN_STORES : [storeFilter];

      for (const s of storesToQuery) {
        try {
          const data: any = await get_store_ads(s.toLowerCase(), week);
          if (!data) continue;
          // Ensure an array
          const arr: any[] = Array.isArray(data) ? data : [data];

          // For each ad, attempt to resolve image (either image_filename or image_base64)
          const annotated: Ad[] = [];
          for (const d of arr) {
            try {
              const ad: Ad = {
                product: d.name ?? d.product ?? "",
                price: d.price ?? d.cost ?? "",
                store: s,
                date: d.date ?? undefined,
              } as Ad;
              const imageVal = (d.image ||
                d.image_filename ||
                d.image_file ||
                d.img) as string | undefined;
              const filename = imageVal;
              if (filename) {
                try {
                  ad.image_filename = filename;
                  ad.image_uri = await get_image(
                    s.toLowerCase(),
                    week,
                    filename
                  );
                } catch (imgErr) {
                  ad.image_uri = null;
                }
              }

              annotated.push(ad);
            } catch (innerErr) {
              // skip problematic ad entries so a single bad item doesn't break the whole batch
              continue;
            }
          }

          results = results.concat(annotated as Ad[]);
        } catch (e) {
          // If one store doesn't have an ad or request failed, skip it
          continue;
        }
      }

      setAds(results);
    } catch (e: any) {
      setError(e.message ?? "Failed to load ads");
    } finally {
      setLoading(false);
    }
  }

  // // Optional local date filter: keeps the existing UI behaviour (YYYY, YYYY-MM or YYYY-MM-DD)
  // const filteredAds = useMemo(() => {
  //   if (!dateFilter) return ads;
  //   const df = dateFilter.trim();
  //   if (/^\d{4}$/.test(df)) return ads.filter((a) => a.date?.startsWith(df));
  //   if (/^\d{4}-\d{2}$/.test(df))
  //     return ads.filter((a) => a.date?.startsWith(df));
  //   if (/^\d{4}-\d{2}-\d{2}$/.test(df)) {
  //     const target = new Date(df);
  //     return ads.filter((a) => {
  //       if (!a.date) return false;
  //       const adDate = new Date(a.date);
  //       if (isNaN(adDate.getTime())) return false;
  //       const msDiff = Math.abs(adDate.getTime() - target.getTime());
  //       return msDiff / (1000 * 60 * 60 * 24) <= 7;
  //     });
  //   }
  //   return ads;
  // }, [ads, dateFilter]);

  function handleDateInput(text: string) {
    const digits = text.replace(/\D/g, "").slice(0, 8);
    let formatted = digits;
    if (digits.length > 4 && digits.length <= 6) {
      formatted = `${digits.slice(0, 4)}-${digits.slice(4)}`;
    } else if (digits.length > 6) {
      formatted = `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(
        6
      )}`;
    }
    setDateFilter(formatted);
  }

  function renderItem({ item, index }: { item: Ad; index: number }) {
    const uri =
      item.image_uri ??
      (item.image_base64
        ? `data:image/png;base64,${item.image_base64}`
        : undefined);
    return (
      <View style={styles.adItem}>
        {uri ? (
          <Image source={{ uri }} style={styles.adImage} contentFit="cover" />
        ) : (
          <View style={[styles.adImage, styles.noImage]}>
            <Text>No image</Text>
          </View>
        )}
        <View style={styles.adContent}>
          <ThemedText type="defaultSemiBold">{item.product}</ThemedText>
          <ThemedText>
            {item.store ?? ""} — {item.date ?? ""}
          </ThemedText>
          <ThemedText>{String(item.price)}</ThemedText>
        </View>
        <View style={styles.addButton}>
          <Button title="Add" onPress={() => addToBasket(item)} />
        </View>
      </View>
    );
  }

  function addToBasket(item: Ad) {
    setBasket((prev) => [...prev, item]);
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Ads</ThemedText>

      <View style={styles.filters}>
        <ThemedText type="subtitle">Store filter</ThemedText>
        <View style={styles.storeRow}>
          {["All", ...KNOWN_STORES].map((s) => {
            const active = storeFilter === s;
            return (
              <Pressable
                key={s}
                onPress={() => setStoreFilter(s)}
                style={[styles.storeChip, active && styles.storeChipActive]}
              >
                <ThemedText type={active ? "defaultSemiBold" : "default"}>
                  {s}
                </ThemedText>
              </Pressable>
            );
          })}
        </View>

        <ThemedText type="subtitle">Date filter</ThemedText>
        <TextInput
          placeholder="YYYY-MM-DD (±7 days)"
          style={styles.input}
          value={dateFilter}
          onChangeText={handleDateInput}
          maxLength={10}
          keyboardType="numeric"
        />

        <View style={{ marginTop: 8 }}>
          <Button title="Refresh" onPress={fetchAdsForSelection} />
        </View>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : error ? (
        <ThemedText style={{ color: "red" }}>{error}</ThemedText>
      ) : (
        <FlatList
          data={ads}
          keyExtractor={(item, idx) => `${item.product}-${idx}`}
          style={styles.list}
          ListEmptyComponent={
            <ThemedText>No ads for the selected store/week.</ThemedText>
          }
          renderItem={renderItem}
        />
      )}
    </ThemedView>
  );
}

/* Helper to get the Monday date (YYYY-MM-DD) for a given date */
function getMondayISO(date: Date) {
  const d = new Date(date.getTime());
  const day = d.getDay(); // 0 (Sun) .. 6 (Sat)
  const diff = day === 0 ? -6 : 1 - day; // shift Sunday to previous Monday
  d.setDate(d.getDate() + diff);
  // Return local YYYY-MM-DD (avoid UTC offset issues from toISOString)
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 12,
  },
  filters: {
    gap: 8,
    marginBottom: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    padding: 8,
    borderRadius: 6,
  },
  list: {
    flex: 1,
  },
  adItem: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
    flexDirection: "row",
    alignItems: "center",
    paddingRight: 8,
  },
  adImage: {
    width: 72,
    height: 72,
    borderRadius: 8,
  },
  noImage: {
    backgroundColor: "#eee",
    alignItems: "center",
    justifyContent: "center",
  },
  adContent: {
    marginLeft: 12,
    flex: 1,
  },
  addButton: {
    width: 84,
    marginLeft: 8,
  },
  storeRow: {
    flexDirection: "row",
    gap: 8,
    flexWrap: "wrap",
  },
  storeChip: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 16,
  },
  storeChipActive: {
    backgroundColor: "#e6f0ff",
    borderColor: "#85aaff",
  },
});
