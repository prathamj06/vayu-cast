import { AQICategory } from "@/types";

export const AQI_CATEGORIES: AQICategory[] = [
  {
    label: "Good",
    label_hi: "अच्छा",
    min: 0,
    max: 50,
    color: "#00E400",
    rgb: [0, 228, 0, 180],
    description: "Air quality is considered satisfactory, and air pollution poses little or no risk.",
    textColor: "#000000"
  },
  {
    label: "Moderate",
    label_hi: "मध्यम",
    min: 51,
    max: 100,
    color: "#FFFF00",
    rgb: [255, 255, 0, 180],
    description: "Air quality is acceptable; however, some pollutants may pose moderate health concern for sensitive individuals.",
    textColor: "#000000"
  },
  {
    label: "Unhealthy for Sensitive Groups",
    label_hi: "संवेदनशील समूहों के लिए अस्वस्थ",
    min: 101,
    max: 150,
    color: "#FF7E00",
    rgb: [255, 126, 0, 180],
    description: "Members of sensitive groups (children, elderly, respiratory patients) may experience health effects.",
    textColor: "#FFFFFF"
  },
  {
    label: "Unhealthy",
    label_hi: "अस्वस्थ",
    min: 151,
    max: 200,
    color: "#FF0000",
    rgb: [255, 0, 0, 180],
    description: "Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.",
    textColor: "#FFFFFF"
  },
  {
    label: "Very Unhealthy",
    label_hi: "बहुत अस्वस्थ",
    min: 201,
    max: 300,
    color: "#8F3F97",
    rgb: [143, 63, 151, 180],
    description: "Health alert: The risk of health effects is increased for everyone.",
    textColor: "#FFFFFF"
  },
  {
    label: "Hazardous",
    label_hi: "गंभीर / खतरनाक",
    min: 301,
    max: 999,
    color: "#7E0023",
    rgb: [126, 0, 35, 195],
    description: "Health warning of emergency conditions: The entire population is more likely to be affected.",
    textColor: "#FFFFFF"
  },
];

export function getAQICategory(aqi: number): AQICategory {
  const rounded = Math.round(aqi);
  for (const cat of AQI_CATEGORIES) {
    if (rounded <= cat.max) {
      return cat;
    }
  }
  return AQI_CATEGORIES[AQI_CATEGORIES.length - 1];
}

export function getAQIColor(aqi: number): string {
  return getAQICategory(aqi).color;
}

export function getAQIRGB(aqi: number, alpha: number = 180): [number, number, number, number] {
  const cat = getAQICategory(aqi);
  return [cat.rgb[0], cat.rgb[1], cat.rgb[2], alpha];
}

export function formatTimeOffset(hoursOffset: number): string {
  if (hoursOffset === 0) return "Live Now";
  return `+${hoursOffset}h Forecast`;
}
