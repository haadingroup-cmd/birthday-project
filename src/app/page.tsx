"use client";

import Starfield from "@/components/Starfield";
import Hero from "@/components/Hero";
import Cake from "@/components/Cake";
import Countdown from "@/components/Countdown";
import Gallery from "@/components/Gallery";
import Timeline from "@/components/Timeline";
import WishWall from "@/components/WishWall";
import Happy from "@/components/Happy";
import EffectsCanvas from "@/components/EffectsCanvas";
import EasterEgg from "@/components/EasterEgg";
import AmbientSound from "@/components/AmbientSound";

export default function Home() {
  return (
    <>
      <Starfield />
      <Hero />
      <Cake />
      <Countdown />
      <Gallery />
      <Timeline />
      <WishWall />
      <Happy />
      <EffectsCanvas />
      <EasterEgg />
      <AmbientSound />
    </>
  );
}
