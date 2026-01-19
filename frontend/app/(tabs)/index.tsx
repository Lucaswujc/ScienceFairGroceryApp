import { Image } from "expo-image";
import { Linking, Pressable, StyleSheet, Text } from "react-native";

import { HelloWave } from "@/components/HelloWave";
import ParallaxScrollView from "@/components/ParallaxScrollView";
import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";

export default function HomeScreen() {
  return (
    <ThemedView style={styles.screen} lightColor="#ffffff" darkColor="#ffffff">
      <ParallaxScrollView
        headerBackgroundColor={{ light: "#A1CEDC", dark: "#1D3D47" }}
        headerImage={
          <Image
            source={require("@/assets/images/partial-react-logo.png")}
            style={styles.reactLogo}
          />
        }
      >
        <ThemedView style={styles.titleContainer}>
          <ThemedText type="title">Hello grocery shoppers,</ThemedText>
          <HelloWave />
        </ThemedView>
        <ThemedView style={styles.stepContainer}>
          <ThemedText type="subtitle">We hope Smart Cart will help you in your daily lives to save money on grocery shopping and reduce personal food waste.</ThemedText>
        </ThemedView>
        <ThemedView style={styles.stepContainer}>
          <ThemedText type="subtitle">App Use:
</ThemedText>
          <ThemedText>
            {`The Ads Section allows you to view weekly promotions from different stores. Click on Pick Monday and select a date. Then, select your grocery store. It may take a few seconds to load the grocery items. From there, you can simply add items to your list and view it in your cart.`}
          </ThemedText>
          <ThemedText>
            {`The Analyze Section is used to help you track items in your fridge that are perishable and need to be restocked soon. Take a picture of the inside of your fridge, and click on analyze. This will generate a list of recommended items in the fridge to eat first. If there are matching promotional items with the list, these items will automatically be added to the cart. `}
          </ThemedText>
        </ThemedView>
        <ThemedView style={styles.stepContainer}>
          <ThemedText type="subtitle">Please share your experience with us at </ThemedText>
          <ThemedText>
            <Pressable onPress={() => Linking.openURL("https://forms.gle/sRiJtqoheh4emanN6")}>
              <Text style={{ color: "#0a7ea4" }}>Smart Cart Feedback Form</Text>
            </Pressable>
          </ThemedText>
        </ThemedView>
      </ParallaxScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  titleContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  stepContainer: {
    gap: 8,
    marginBottom: 8,
  },
  reactLogo: {
    height: 178,
    width: 290,
    bottom: 0,
    left: 0,
    position: "absolute",
  },
});
