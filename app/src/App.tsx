import { Browser } from "@/components/Browser";
import { PhoneApp } from "@/components/PhoneApp";
import { useNarrow } from "@/lib/narrow";
import { appNetwork } from "@/lib/network";

function App() {
  const narrow = useNarrow();
  return narrow ? <PhoneApp /> : <Browser local={appNetwork().this_machine} />;
}

export default App;
