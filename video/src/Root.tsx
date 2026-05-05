import React from "react";
import "./index.css";
import { Composition } from "remotion";
import { BotBudgetAd } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BotBudgetAd"
        component={BotBudgetAd}
        durationInFrames={450}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
