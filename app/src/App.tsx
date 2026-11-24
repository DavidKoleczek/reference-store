import { SettingsMenu } from "@/components/SettingsMenu";
import { Wordmark } from "@/components/Wordmark";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";

function App() {
  return (
    <div className="flex h-screen flex-col bg-canvas text-ink">
      <header className="flex h-10 shrink-0 items-center gap-2 border-b bg-panel pr-2 pl-3">
        <Wordmark />
        <span className="flex-1" />
        <SettingsMenu />
      </header>
      <main className="grid min-h-0 flex-1 place-items-center p-6">
        <EmptyState
          tile={<Icon name="folder" size={24} />}
          tileClassName="bg-pastel-butter"
          title="Nothing here yet"
          className="w-full max-w-sm"
        />
      </main>
    </div>
  );
}

export default App;
