//! Interactive chart of NixOS build and activation durations recorded by
//! `nixos-rebuild-desktop` and the `nh` wrapper in `times.csv`
//! (`started,operation,seconds,exit[,via]`).
use anyhow::{Context, Result, bail};
use chrono::{DateTime, Local, Utc};
use crossterm::event::{
    self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind, KeyModifiers,
    MouseButton, MouseEventKind,
};
use ratatui::{
    Frame,
    layout::{Alignment, Constraint, Layout, Position, Rect},
    style::{Color, Modifier, Style},
    symbols::Marker,
    text::{Line, Span},
    widgets::{
        Axis, Block, Borders, Cell, Chart, Dataset, GraphType, Paragraph, Row, Table, TableState,
    },
};
use std::{io, path::PathBuf};

#[derive(Clone, Debug, PartialEq)]
struct Build {
    started: DateTime<Utc>,
    seconds: u64,
    /// The first successful activation before the next build, if any.
    activation: Option<u64>,
    /// The rebuild tool, when it was not `nixos-rebuild-desktop`.
    via: Option<String>,
}

fn parse(text: &str) -> Vec<Build> {
    let mut builds: Vec<Build> = Vec::new();
    let mut awaiting_activation = false;
    for line in text.lines() {
        let fields: Vec<_> = line.trim().split(',').collect();
        let (started, operation, seconds, status, via) = match fields[..] {
            [started, operation, seconds, status] => (started, operation, seconds, status, None),
            [started, operation, seconds, status, via] => {
                (started, operation, seconds, status, Some(via.to_string()))
            }
            _ => continue,
        };
        let (Ok(started), Ok(seconds)) = (started.parse::<DateTime<Utc>>(), seconds.parse()) else {
            continue;
        };
        let ok = status == "0";
        match operation {
            "build" => {
                awaiting_activation = ok;
                if ok {
                    builds.push(Build {
                        started,
                        seconds,
                        activation: None,
                        via,
                    });
                }
            }
            "activate" if ok && awaiting_activation => {
                if let Some(last) = builds.last_mut() {
                    last.activation = Some(seconds);
                }
                awaiting_activation = false;
            }
            _ => {}
        }
    }
    builds
}

fn duration(seconds: u64) -> String {
    match seconds {
        0..60 => format!("{seconds}s"),
        60..3600 => format!("{}m {:02}s", seconds / 60, seconds % 60),
        _ => format!("{}h {:02}m", seconds / 3600, seconds % 3600 / 60),
    }
}

fn median(builds: &[Build]) -> u64 {
    let mut values: Vec<_> = builds.iter().map(|b| b.seconds).collect();
    values.sort_unstable();
    let n = values.len();
    match n {
        0 => 0,
        _ if n % 2 == 1 => values[n / 2],
        _ => (values[n / 2 - 1] + values[n / 2]) / 2,
    }
}

/// Eighth-block characters give the bars sub-cell resolution.
fn bar(value: u64, longest: u64, width: usize) -> String {
    if longest == 0 {
        return String::new();
    }
    let eighths = (value as f64 / longest as f64 * width as f64 * 8.0).round() as usize;
    let mut out = "█".repeat(eighths / 8);
    if !eighths.is_multiple_of(8) {
        out.push(['▏', '▎', '▍', '▌', '▋', '▊', '▉'][eighths % 8 - 1]);
    }
    out
}

fn local(time: DateTime<Utc>, format: &str) -> String {
    time.with_timezone(&Local).format(format).to_string()
}

struct App {
    path: PathBuf,
    builds: Vec<Build>,
    table: TableState,
    time_axis: bool,
    show_activation: bool,
    table_area: Rect,
    chart_area: Rect,
    error: Option<String>,
}

impl App {
    fn load(path: PathBuf) -> Result<Self> {
        let mut app = Self {
            path,
            builds: Vec::new(),
            table: TableState::default(),
            time_axis: false,
            show_activation: true,
            table_area: Rect::default(),
            chart_area: Rect::default(),
            error: None,
        };
        app.reload()?;
        Ok(app)
    }
    fn reload(&mut self) -> Result<()> {
        let text = std::fs::read_to_string(&self.path)
            .with_context(|| format!("Read {}", self.path.display()))?;
        self.builds = parse(&text);
        if self.builds.is_empty() {
            bail!("No successful timed builds yet: {}", self.path.display());
        }
        self.table.select(Some(self.builds.len() - 1));
        Ok(())
    }
    fn selected(&self) -> usize {
        self.table
            .selected()
            .unwrap_or(0)
            .min(self.builds.len() - 1)
    }
    fn select(&mut self, index: isize) {
        let last = self.builds.len() as isize - 1;
        self.table.select(Some(index.clamp(0, last) as usize));
    }
    fn x(&self, index: usize) -> f64 {
        if self.time_axis {
            (self.builds[index].started - self.builds[0].started).num_seconds() as f64 / 3600.0
        } else {
            index as f64
        }
    }
    /// The build whose chart position is closest to a column inside the plot.
    fn nearest(&self, fraction: f64) -> usize {
        let (low, high) = self.x_bounds();
        let target = low + fraction * (high - low);
        (0..self.builds.len())
            .min_by(|&a, &b| {
                (self.x(a) - target)
                    .abs()
                    .total_cmp(&(self.x(b) - target).abs())
            })
            .unwrap_or(0)
    }
    fn x_bounds(&self) -> (f64, f64) {
        let high = self.x(self.builds.len() - 1);
        if high <= 0.0 { (0.0, 1.0) } else { (0.0, high) }
    }
}

const GREEN: Color = Color::Green;
const BLUE: Color = Color::Cyan;
const ACCENT: Color = Color::Yellow;

fn muted() -> Style {
    Style::default().add_modifier(Modifier::DIM)
}

fn draw(frame: &mut Frame, app: &mut App) {
    let [header, chart, table, footer] = Layout::vertical([
        Constraint::Length(2),
        Constraint::Percentage(55),
        Constraint::Min(5),
        Constraint::Length(1),
    ])
    .areas(frame.area().inner(ratatui::layout::Margin::new(1, 0)));
    draw_header(frame, header, app);
    draw_chart(frame, chart, app);
    draw_table(frame, table, app);
    let keys = if let Some(error) = &app.error {
        Line::styled(error.clone(), Style::default().fg(Color::Red))
    } else {
        Line::styled(
            "j/k · wheel · click select   g/G first/last   t time axis   a activations   r reload   q quit",
            muted(),
        )
    };
    frame.render_widget(Paragraph::new(keys), footer);
}

fn draw_header(frame: &mut Frame, area: Rect, app: &App) {
    let builds = &app.builds;
    let slowest = builds.iter().map(|b| b.seconds).max().unwrap_or(0);
    let fastest = builds.iter().map(|b| b.seconds).min().unwrap_or(0);
    let stat = |name: &str, value: u64| {
        [
            Span::styled(format!("  {name} "), muted()),
            Span::styled(
                duration(value),
                Style::default().add_modifier(Modifier::BOLD),
            ),
        ]
    };
    let mut spans = vec![
        Span::styled(
            " NixOS build times ",
            Style::default()
                .fg(ACCENT)
                .add_modifier(Modifier::BOLD | Modifier::REVERSED),
        ),
        Span::styled(format!("  {} successful builds", builds.len()), muted()),
    ];
    spans.extend(stat("median", median(builds)));
    spans.extend(stat("fastest", fastest));
    spans.extend(stat("slowest", slowest));
    spans.extend(stat("last", builds.last().map_or(0, |b| b.seconds)));
    frame.render_widget(Paragraph::new(Line::from(spans)), area);
}

fn draw_chart(frame: &mut Frame, area: Rect, app: &mut App) {
    app.chart_area = area;
    let minutes = |s: u64| s as f64 / 60.0;
    let builds: Vec<(f64, f64)> = (0..app.builds.len())
        .map(|i| (app.x(i), minutes(app.builds[i].seconds)))
        .collect();
    let activations: Vec<(f64, f64)> = (0..app.builds.len())
        .filter_map(|i| Some((app.x(i), minutes(app.builds[i].activation?))))
        .collect();
    let (x_low, x_high) = app.x_bounds();
    let typical = minutes(median(&app.builds));
    let median_line = [(x_low, typical), (x_high, typical)];
    let selected = app.selected();
    let marker = [builds[selected]];
    let peak = app
        .builds
        .iter()
        .flat_map(|b| [b.seconds, b.activation.unwrap_or(0)])
        .max()
        .unwrap_or(60);
    // Round the axis up to a whole number of minutes with some headroom.
    let y_high = (minutes(peak) * 1.1).ceil().max(1.0);

    let mut datasets = vec![
        Dataset::default()
            .name("median")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(muted())
            .data(&median_line),
    ];
    if app.show_activation {
        datasets.push(
            Dataset::default()
                .name("activate")
                .marker(Marker::Braille)
                .graph_type(GraphType::Line)
                .style(Style::default().fg(BLUE))
                .data(&activations),
        );
    }
    datasets.extend([
        Dataset::default()
            .name("build")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::default().fg(GREEN))
            .data(&builds),
        Dataset::default()
            .marker(Marker::Block)
            .graph_type(GraphType::Scatter)
            .style(Style::default().fg(ACCENT))
            .data(&marker),
    ]);

    let x_labels: Vec<Line> = if app.time_axis {
        let first = app.builds[0].started;
        [0.0, 0.5, 1.0]
            .iter()
            .map(|f| {
                let at = first + chrono::Duration::seconds((x_high * f * 3600.0) as i64);
                Line::from(local(at, "%d %b %H:%M"))
            })
            .collect()
    } else {
        let last = app.builds.len() - 1;
        [0, last / 2, last]
            .iter()
            .map(|&i| Line::from(local(app.builds[i].started, "%d %b")))
            .collect()
    };
    let y_labels = [0.0, y_high / 2.0, y_high].map(|m| Line::from(format!("{m:.0}m")));
    let b = &app.builds[selected];
    let title = Line::from(vec![
        Span::raw(" "),
        Span::styled(format!("#{} ", selected + 1), Style::default().fg(ACCENT)),
        Span::raw(local(b.started, "%a %d %b %H:%M")),
        Span::styled(
            b.via
                .as_ref()
                .map_or(String::new(), |via| format!(" via {via}")),
            muted(),
        ),
        Span::styled("  build ", muted()),
        Span::styled(
            duration(b.seconds),
            Style::default().fg(GREEN).add_modifier(Modifier::BOLD),
        ),
        Span::styled("  activate ", muted()),
        Span::styled(
            b.activation.map_or("—".into(), duration),
            Style::default().fg(BLUE),
        ),
        Span::raw(" "),
    ]);
    let chart = Chart::new(datasets)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(muted())
                .title(title)
                .title_bottom(
                    Line::from(if app.time_axis {
                        " x: time "
                    } else {
                        " x: build "
                    })
                    .alignment(Alignment::Right)
                    .style(muted()),
                ),
        )
        .x_axis(
            Axis::default()
                .bounds([x_low, x_high])
                .labels(x_labels)
                .style(muted()),
        )
        .y_axis(
            Axis::default()
                .bounds([0.0, y_high])
                .labels(y_labels)
                .style(muted()),
        )
        .legend_position(Some(ratatui::widgets::LegendPosition::TopLeft))
        .hidden_legend_constraints((Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)));
    frame.render_widget(chart, area);
}

fn draw_table(frame: &mut Frame, area: Rect, app: &mut App) {
    app.table_area = area;
    let longest = app.builds.iter().map(|b| b.seconds).max().unwrap_or(0);
    let bar_width = usize::from(area.width.saturating_sub(4 + 20 + 9 + 10 + 6)).clamp(8, 80);
    let selected = app.selected();
    let rows = app.builds.iter().enumerate().map(|(i, b)| {
        // Reversing the whole row would invert the bar glyphs and hide the bar,
        // so the selection is a label tag plus a bar in the chart marker color.
        let (label, bar_style, emphasis) = if i == selected {
            (
                Style::default()
                    .fg(ACCENT)
                    .add_modifier(Modifier::REVERSED | Modifier::BOLD),
                Style::default().fg(ACCENT),
                Style::default().add_modifier(Modifier::BOLD),
            )
        } else {
            (muted(), Style::default().fg(GREEN), Style::default())
        };
        Row::new([
            Cell::from(format!(
                "{:>3} {} {}",
                i + 1,
                local(b.started, "%a %d %b %H:%M"),
                b.via.as_deref().unwrap_or("")
            ))
            .style(label),
            Cell::from(bar(b.seconds, longest, bar_width)).style(bar_style),
            Cell::from(Line::from(duration(b.seconds)).alignment(Alignment::Right)).style(emphasis),
            Cell::from(
                Line::from(b.activation.map_or("—".into(), duration)).alignment(Alignment::Right),
            )
            .style(emphasis.fg(BLUE)),
        ])
    });
    let header = Row::new([
        Cell::from("  # started"),
        Cell::from(""),
        Cell::from(Line::from("build").alignment(Alignment::Right)),
        Cell::from(Line::from("activate").alignment(Alignment::Right)),
    ])
    .style(muted().add_modifier(Modifier::BOLD));
    let table = Table::new(
        rows,
        [
            Constraint::Length(23),
            Constraint::Length(bar_width as u16),
            Constraint::Length(9),
            Constraint::Length(10),
        ],
    )
    .header(header)
    .column_spacing(1)
    .highlight_symbol(Span::styled("▐", Style::default().fg(ACCENT)))
    .block(Block::default().borders(Borders::TOP).border_style(muted()));
    frame.render_stateful_widget(table, area, &mut app.table);
}

enum Flow {
    Continue,
    Quit,
}

fn handle(app: &mut App, input: Event) -> Flow {
    let selected = app.selected() as isize;
    match input {
        Event::Key(key) if key.kind != KeyEventKind::Release => {
            let ctrl = key.modifiers.contains(KeyModifiers::CONTROL);
            match key.code {
                KeyCode::Char('q') | KeyCode::Esc => return Flow::Quit,
                KeyCode::Char('c') if ctrl => return Flow::Quit,
                KeyCode::Char('j') | KeyCode::Down | KeyCode::Right | KeyCode::Char('l') => {
                    app.select(selected + 1)
                }
                KeyCode::Char('k') | KeyCode::Up | KeyCode::Left | KeyCode::Char('h') => {
                    app.select(selected - 1)
                }
                KeyCode::Char('g') | KeyCode::Home => app.select(0),
                KeyCode::Char('G') | KeyCode::End => app.select(isize::MAX),
                KeyCode::Char('t') => app.time_axis = !app.time_axis,
                KeyCode::Char('a') => app.show_activation = !app.show_activation,
                KeyCode::Char('r') => {
                    app.error = app.reload().err().map(|e| format!("{e:#}"));
                }
                _ => {}
            }
        }
        Event::Mouse(mouse) => {
            let at = Position::new(mouse.column, mouse.row);
            match mouse.kind {
                MouseEventKind::ScrollDown => app.select(selected + 1),
                MouseEventKind::ScrollUp => app.select(selected - 1),
                MouseEventKind::Down(MouseButton::Left) if app.table_area.contains(at) => {
                    // Rows start below the top border and the header.
                    let row = at.y.saturating_sub(app.table_area.y + 2);
                    if at.y >= app.table_area.y + 2 {
                        app.select((app.table.offset() + usize::from(row)) as isize);
                    }
                }
                MouseEventKind::Down(MouseButton::Left) if app.chart_area.contains(at) => {
                    let area = app.chart_area;
                    let fraction = f64::from(at.x.saturating_sub(area.x))
                        / f64::from(area.width.saturating_sub(1).max(1));
                    app.select(app.nearest(fraction) as isize);
                }
                _ => {}
            }
        }
        _ => {}
    }
    Flow::Continue
}

fn main() -> Result<()> {
    let path = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .context("Usage: build-times TIMES.csv")?;
    let mut app = App::load(path)?;
    let mut terminal = ratatui::init();
    let _ = crossterm::execute!(io::stdout(), EnableMouseCapture);
    let result = (|| -> Result<()> {
        loop {
            terminal.draw(|f| draw(f, &mut app))?;
            if let Flow::Quit = handle(&mut app, event::read()?) {
                return Ok(());
            }
        }
    })();
    let _ = crossterm::execute!(io::stdout(), DisableMouseCapture);
    ratatui::restore();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{Terminal, backend::TestBackend};

    const SAMPLE: &str = "\
2026-10-29T22:58:47Z,activate,3,1
2026-11-02T16:29:46Z,build,622,0
2026-11-02T16:40:21Z,activate,122,0
2026-11-02T16:50:00Z,activate,9,0
2026-11-02T17:00:00Z,build,5,1
2026-11-02T17:01:00Z,activate,7,0
garbage
2026-11-03T22:45:34Z,build,45,0
2026-11-04T10:00:00Z,build,90,0,nh
2026-11-04T10:01:30Z,activate,20,0,nh
";

    #[test]
    fn pairs_each_successful_build_with_its_first_activation() {
        let builds = parse(SAMPLE);
        assert_eq!(builds.len(), 3);
        assert_eq!((builds[0].seconds, builds[0].activation), (622, Some(122)));
        assert_eq!((builds[1].seconds, builds[1].activation), (45, None));
        assert_eq!(builds[1].via, None);
        assert_eq!((builds[2].seconds, builds[2].activation), (90, Some(20)));
        assert_eq!(builds[2].via.as_deref(), Some("nh"));
    }

    #[test]
    fn formats_durations_bars_and_median() {
        assert_eq!(duration(45), "45s");
        assert_eq!(duration(622), "10m 22s");
        assert_eq!(duration(3725), "1h 02m");
        assert_eq!(bar(10, 10, 4), "████");
        assert_eq!(bar(5, 10, 3), "█▌");
        assert_eq!(median(&parse(SAMPLE)), 90);
    }

    fn screen(app: &mut App, width: u16, height: u16) -> String {
        let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
        terminal.draw(|f| draw(f, app)).unwrap();
        let buffer = terminal.backend().buffer();
        (0..buffer.area.height)
            .map(|y| {
                (0..buffer.area.width)
                    .map(|x| buffer[(x, y)].symbol())
                    .collect::<String>()
                    + "\n"
            })
            .collect()
    }

    /// Each test gets its own file because tests run concurrently.
    fn sample_app(name: &str) -> App {
        let dir = std::env::temp_dir().join(format!("build-times-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(format!("{name}.csv"));
        std::fs::write(&path, SAMPLE).unwrap();
        App::load(path).unwrap()
    }

    #[test]
    fn selected_row_keeps_its_bar_visible() {
        let mut app = sample_app("selected-bar");
        let mut terminal = Terminal::new(TestBackend::new(120, 40)).unwrap();
        terminal.draw(|f| draw(f, &mut app)).unwrap();
        let buffer = terminal.backend().buffer();
        let row = (0..buffer.area.height)
            .find(|&y| buffer[(1, y)].symbol() == "▐")
            .expect("selected row marker");
        let bar: Vec<_> = (0..buffer.area.width)
            .map(|x| &buffer[(x, row)])
            .filter(|cell| cell.symbol() == "█")
            .collect();
        assert!(!bar.is_empty());
        assert!(
            bar.iter()
                .all(|cell| cell.fg == ACCENT && !cell.modifier.contains(Modifier::REVERSED))
        );
    }

    #[test]
    fn renders_chart_and_table_and_follows_selection() {
        let mut app = sample_app("render");
        for (w, h) in [(60, 20), (120, 40)] {
            let text = screen(&mut app, w, h);
            assert!(text.contains("NixOS build times"));
            assert!(text.contains("10m 22s"));
            assert!(text.contains("activate"));
        }
        assert_eq!(app.selected(), 2);
        assert!(screen(&mut app, 120, 40).contains("via nh"));
        handle(&mut app, Event::Key(KeyCode::Char('g').into()));
        assert_eq!(app.selected(), 0);
        handle(&mut app, Event::Key(KeyCode::Char('t').into()));
        assert!(app.time_axis);
        assert!(screen(&mut app, 100, 30).contains("x: time"));
        assert_eq!(app.nearest(1.0), 2);
    }
}
