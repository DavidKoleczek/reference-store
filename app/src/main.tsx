import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Notice } from "@/components/ui/notice";
import { describe } from "@/lib/errors";
import { connect } from "@/lib/host";
import { loadNetwork } from "@/lib/network";
import { loadSettings } from "@/lib/settings";
import { TEXT } from "@/lib/text";

const root = createRoot(document.getElementById("root")!);

try {
  await connect();
  await Promise.all([loadSettings(), loadNetwork()]);
  root.render(
    <StrictMode>
      <TooltipProvider>
        <ErrorBoundary what={TEXT.errors.theApp} className="m-4">
          <App />
        </ErrorBoundary>
      </TooltipProvider>
    </StrictMode>,
  );
} catch (cause) {
  root.render(
    <Notice title={TEXT.errors.noHost} className="m-4">
      {describe(cause)}
    </Notice>,
  );
}
