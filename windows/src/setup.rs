//! Setup: a window that asks what to install, shows the install as it runs, and opens the app at the end. The window
//! holds a page from `ui/`, shown in Windows' web view. An update is the same window, with nothing to ask.

use std::borrow::Cow;
use std::path::PathBuf;
use std::process::Command;
use std::thread;

use serde_json::{Value, json};
use tao::dpi::{LogicalSize, PhysicalPosition};
use tao::event::{Event as LoopEvent, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop, EventLoopBuilder, EventLoopProxy};
use tao::platform::run_return::EventLoopExtRunReturn;
use tao::platform::windows::{IconExtWindows, WindowExtWindows};
use tao::window::{Icon, Theme, Window, WindowBuilder};
use wry::http::header::CONTENT_TYPE;
use wry::http::{HeaderValue, Response, StatusCode};
use wry::{NewWindowResponse, WebContext, WebView, WebViewBuilder, WebViewBuilderExtWindows};

use crate::failure::{Failure, OrSay, Outcome};
use crate::install::{self, Existing, Options, Progress, Shortcuts};
use crate::package::{APP_NAME, VERSION};
use crate::paths::Paths;
use crate::startup::BACKGROUND;
use crate::win32;

const TITLE: &str = "Reference Store Setup";
const SIZE: LogicalSize<f64> = LogicalSize::new(520.0, 580.0);
const UPDATE_TITLE: &str = "Reference Store Update";
const UPDATE_SIZE: LogicalSize<f64> = LogicalSize::new(520.0, 380.0);
// The page's own name for where it is served from, and what WebView2 makes of it.
const SCHEME: &str = "setup";
const PAGE: &str = "setup://localhost/";
const ORIGIN: &str = "http://setup.localhost/";
// The page's ground in each theme, so the window isn't white while it loads.
const LIGHT_PANEL: (u8, u8, u8, u8) = (0xff, 0xff, 0xff, 0xff);
const DARK_PANEL: (u8, u8, u8, u8) = (0x17, 0x1b, 0x21, 0xff);
// The id winresource gives the exe's icon.
const ICON_RESOURCE: u16 = 1;
const WEBVIEW2: &str = "https://developer.microsoft.com/microsoft-edge/webview2/";

/// What the window is opened for.
#[derive(Clone, Copy)]
pub enum Purpose {
    /// Asking what to install, and installing it.
    Install,
    /// Installing this exe over the app that downloaded it, as that one was set up, and starting the app again.
    Update,
}

/// What setup is told of: the page from the web view's own callback, and the rest from other threads.
enum Event {
    /// What the page asked, as it sent it.
    Page(String),
    Found(Existing),
    Progress(Progress),
    Installed(Outcome<()>),
}

struct Setup<'a> {
    paths: &'a Paths,
    purpose: Purpose,
    tell: EventLoopProxy<Event>,
    window: &'a Window,
    page: &'a WebView,
    installing: bool,
    /// Whether an update failed, which had the app quit first.
    update_failed: bool,
}

/// Shows setup, or an update, and returns once its window is closed.
pub fn run(paths: &Paths, purpose: Purpose) -> Outcome<()> {
    if wry::webview_version().is_err() {
        return match purpose {
            Purpose::Install => offer_web_view(),
            Purpose::Update => update_unseen(paths),
        };
    }
    let failed = || "Setup's window couldn't be opened".to_owned();
    let mut event_loop = EventLoopBuilder::<Event>::with_user_event().build();
    let window = open_window(&event_loop, purpose).or_say(failed)?;
    let tell = event_loop.create_proxy();
    let from_page = tell.clone();
    // WebView2 otherwise keeps its files beside the exe, which is wherever it was downloaded to.
    let mut context = WebContext::new(Some(paths.local.join("webview")));
    let page = WebViewBuilder::new_with_web_context(&mut context)
        .with_custom_protocol(SCHEME.to_owned(), |_, request| asset(request.uri().path()))
        .with_url(PAGE)
        // The page is answered from the loop and not from here, inside WebView2's own callback, where opening
        // another window would hang it.
        .with_ipc_handler(move |request| drop(from_page.send_event(Event::Page(request.into_body()))))
        .with_navigation_handler(|url| url.starts_with(ORIGIN))
        .with_new_window_req_handler(|_, _| NewWindowResponse::Deny)
        .with_background_color(if window.theme() == Theme::Dark { DARK_PANEL } else { LIGHT_PANEL })
        .with_browser_accelerator_keys(false)
        .with_default_context_menus(false)
        .with_hotkeys_zoom(false)
        .build(&window)
        .or_say(failed)?;
    window.set_visible(true);

    let mut setup =
        Setup { paths, purpose, tell, window: &window, page: &page, installing: false, update_failed: false };
    event_loop.run_return(|event, _, flow| {
        let going = match event {
            // Closing it would end an install halfway.
            LoopEvent::WindowEvent { event: WindowEvent::CloseRequested, .. } => setup.installing,
            LoopEvent::UserEvent(event) => setup.handle(event),
            _ => true,
        };
        *flow = if going { ControlFlow::Wait } else { ControlFlow::Exit };
    });
    if setup.update_failed {
        // The app is started again as the update left it, which is where to update from again. If it can't be,
        // there is no window left to say so in.
        let _ = Command::new(paths.exe()).arg(BACKGROUND).spawn();
    }
    Ok(())
}

fn offer_web_view() -> Outcome<()> {
    let question = "Setup needs Microsoft Edge WebView2, which this computer doesn't have.\n\n\
                    Open Microsoft's page to download it? Open setup again once it is installed.";
    if win32::ask(APP_NAME, question) {
        win32::open_in_browser(WEBVIEW2).or_say(|| format!("The browser couldn't be opened on {WEBVIEW2}"))?;
    }
    Ok(())
}

/// Updates with no window to show it in, on a computer whose web view has gone since the app was set up.
fn update_unseen(paths: &Paths) -> Outcome<()> {
    let options = Existing::find(paths).kept()?;
    install::install(&options, paths, &mut |_| {})?;
    let mut app = Command::new(paths.exe());
    app.arg(BACKGROUND).spawn().or_say(|| format!("{APP_NAME} was updated, but couldn't be started again"))?;
    Ok(())
}

/// Opens the window in the middle of the main screen, not yet shown.
fn open_window(event_loop: &EventLoop<Event>, purpose: Purpose) -> Result<Window, tao::error::OsError> {
    let (title, size) = match purpose {
        Purpose::Install => (TITLE, SIZE),
        Purpose::Update => (UPDATE_TITLE, UPDATE_SIZE),
    };
    let window = WindowBuilder::new()
        .with_title(title)
        .with_inner_size(size)
        .with_resizable(false)
        .with_maximizable(false)
        .with_window_icon(Icon::from_resource(ICON_RESOURCE, None).ok())
        .with_visible(false)
        .build(event_loop)?;
    if let Some(screen) = window.primary_monitor() {
        let (screen_size, size) = (screen.size(), window.outer_size());
        let middle = |start: i32, around: u32, length: u32| {
            start + (i32::try_from(around).unwrap_or(0) - i32::try_from(length).unwrap_or(0)) / 2
        };
        window.set_outer_position(PhysicalPosition::new(
            middle(screen.position().x, screen_size.width, size.width),
            middle(screen.position().y, screen_size.height, size.height),
        ));
    }
    Ok(window)
}

/// Returns a file of the page, all of which the exe carries.
fn asset(path: &str) -> Response<Cow<'static, [u8]>> {
    let (kind, file): (&str, &[u8]) = match path {
        "/" => ("text/html", include_bytes!("../ui/index.html")),
        "/setup.css" => ("text/css", include_bytes!("../ui/setup.css")),
        "/setup.js" => ("text/javascript", include_bytes!("../ui/setup.js")),
        "/fonts/geist-latin.woff2" => ("font/woff2", include_bytes!("../ui/fonts/geist-latin.woff2")),
        "/fonts/geist-mono-latin.woff2" => ("font/woff2", include_bytes!("../ui/fonts/geist-mono-latin.woff2")),
        _ => {
            let mut missing = Response::new(Cow::Borrowed(&[][..]));
            *missing.status_mut() = StatusCode::NOT_FOUND;
            return missing;
        }
    };
    let mut response = Response::new(Cow::Borrowed(file));
    response.headers_mut().insert(CONTENT_TYPE, HeaderValue::from_static(kind));
    response
}

impl Setup<'_> {
    /// Returns whether setup is to go on.
    fn handle(&mut self, event: Event) -> bool {
        match event {
            Event::Page(message) => return self.asked(&message),
            Event::Found(existing) => match self.purpose {
                Purpose::Install => self.show(&ready(&existing)),
                Purpose::Update => self.update(existing),
            },
            Event::Progress(Progress::Started(stage)) => self.show(&json!({ "is": "started", "label": stage.label() })),
            Event::Progress(Progress::Note(text)) => self.show(&json!({ "is": "note", "text": text })),
            Event::Installed(outcome) => {
                self.installing = false;
                match (outcome, self.purpose) {
                    (Err(failure), purpose) => {
                        self.update_failed = matches!(purpose, Purpose::Update);
                        self.fail(&failure);
                    }
                    (Ok(()), Purpose::Install) => self.show(&json!({ "is": "installed" })),
                    // The app is back by the clock, which is all there is left to show.
                    (Ok(()), Purpose::Update) => return !self.start_app(true),
                }
            }
        }
        true
    }

    /// Does what the page asked, and returns whether setup is to go on.
    fn asked(&mut self, message: &str) -> bool {
        let message: Value = serde_json::from_str(message).unwrap_or_default();
        match message["do"].as_str() {
            Some("ready") => {
                let (paths, tell) = (self.paths.clone(), self.tell.clone());
                thread::spawn(move || drop(tell.send_event(Event::Found(Existing::find(&paths)))));
            }
            Some("browse") => match win32::pick_folder(self.window.hwnd(), "Choose a folder for your first store") {
                Ok(Some(folder)) => self.show(&json!({ "is": "folder", "folder": folder })),
                Ok(None) => {}
                Err(error) => self.fail(&Failure::new(format!("The folder couldn't be asked for: {error}"))),
            },
            Some("install") => self.install(chosen(&message)),
            Some("open") => return !self.start_app(false),
            Some("close") => return false,
            _ => {}
        }
        true
    }

    /// Starts the installed app, in the background or with the browser opened on it, and returns whether it did.
    fn start_app(&self, background: bool) -> bool {
        let mut app = Command::new(self.paths.exe());
        if background {
            app.arg(BACKGROUND);
        }
        let started = app.spawn();
        if let Err(error) = &started {
            self.fail(&Failure::new(format!("{APP_NAME} couldn't be opened: {error}")));
        }
        started.is_ok()
    }

    fn update(&mut self, existing: Existing) {
        self.show(&json!({ "is": "updating", "version": VERSION, "installed": existing.version }));
        match existing.kept() {
            Ok(options) => self.install(options),
            Err(failure) => self.fail(&failure),
        }
    }

    fn install(&mut self, options: Options) {
        if let Some(folder) = options.store.as_ref().filter(|folder| !folder.is_absolute()) {
            let whole = self.paths.documents.join(APP_NAME);
            return self.fail(&Failure::new(format!(
                "{} isn't a whole path. Give the first store's folder from its drive, as in {}.",
                folder.display(),
                whole.display()
            )));
        }
        self.installing = true;
        let (paths, tell) = (self.paths.clone(), self.tell.clone());
        thread::spawn(move || {
            let outcome = install::install(&options, &paths, &mut |progress| {
                drop(tell.send_event(Event::Progress(progress)));
            });
            drop(tell.send_event(Event::Installed(outcome)));
        });
    }

    fn fail(&self, failure: &Failure) {
        self.show(&json!({ "is": "failed", "text": failure.to_string() }));
    }

    /// Hands the page something to show. JSON is also how JavaScript writes the same value.
    fn show(&self, message: &Value) {
        // A page that can't be told has nothing to show the reason on either.
        let _ = self.page.evaluate_script(&format!("window.setup.show({message})"));
    }
}

/// Reads what the page says was chosen.
fn chosen(message: &Value) -> Options {
    let chose = |name: &str| message[name].as_bool().unwrap_or(false);
    Options {
        store: message["store"].as_str().filter(|folder| !folder.is_empty()).map(PathBuf::from),
        lan: chose("lan"),
        shortcuts: Shortcuts { desktop: chose("desktopShortcut"), start_menu: chose("startMenuShortcut") },
        start_at_sign_in: chose("startAtSignIn"),
    }
}

fn ready(existing: &Existing) -> Value {
    let options = &existing.options;
    json!({
        "is": "ready",
        "version": VERSION,
        "installed": existing.version,
        "hasStores": existing.has_stores,
        "store": options.store.clone().unwrap_or_default(),
        "lan": options.lan,
        "desktopShortcut": options.shortcuts.desktop,
        "startMenuShortcut": options.shortcuts.start_menu,
        "startAtSignIn": options.start_at_sign_in,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_page_and_everything_it_loads_is_in_the_exe() {
        let page = String::from_utf8_lossy(include_bytes!("../ui/index.html"));
        let styles = String::from_utf8_lossy(include_bytes!("../ui/setup.css"));
        let loaded = page
            .split(['"', '\''])
            .chain(styles.split('"'))
            .filter(|word| [".css", ".js", ".woff2"].iter().any(|kind| word.ends_with(kind)));
        let mut count = 0;
        for file in loaded {
            assert_eq!(asset(&format!("/{file}")).status(), StatusCode::OK, "{file}");
            count += 1;
        }
        assert_eq!(count, 4);
        assert_eq!(asset("/").headers()[CONTENT_TYPE], "text/html");
        assert_eq!(asset("/setup.exe").status(), StatusCode::NOT_FOUND);
    }

    #[test]
    fn the_page_is_told_what_is_there_in_its_own_words() {
        let existing = Existing {
            version: Some("0.1.0".to_owned()),
            has_stores: true,
            options: Options {
                lan: true,
                shortcuts: Shortcuts { desktop: false, start_menu: true },
                ..Options::default()
            },
        };
        let told = ready(&existing);
        assert_eq!(told["installed"], "0.1.0");
        assert_eq!(told["store"], "");
        assert_eq!(
            (&told["lan"], &told["desktopShortcut"], &told["startMenuShortcut"]),
            (&json!(true), &json!(false), &json!(true))
        );
        // Every switch the page has is told, by the name the page knows it by.
        let script = include_str!("../ui/setup.js");
        for name in ["lan", "desktopShortcut", "startMenuShortcut", "startAtSignIn"] {
            assert!(told[name].is_boolean() && script.contains(&format!("{name}: element(")), "{name}");
        }
    }
}
