"""Graphical interface for the PowRAR compression suite."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List, Optional

from .compression import (
    CompressionSettings,
    DecompressionSettings,
    OperationCancelled,
    compress,
    decompress,
    default_archive_name,
)


@dataclass
class _TaskRequest:
    kind: str  # "compress" or "decompress"
    sources: List[Path]
    destination: Path
    level: int


class PowRARApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PowRAR - Compactação Extremamente Rápida")
        self.geometry("720x520")
        self.minsize(640, 480)

        self._items: List[Path] = []
        self._worker: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._queue: "queue.Queue[tuple[str, object]]" = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # -- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Label(
            self,
            text=(
                "Arraste arquivos e pastas ou use os botões abaixo para criar\n"
                "arquivos .pwr com compactação ultra eficiente."
            ),
            anchor="center",
            justify="center",
            font=("Segoe UI", 11),
        )
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        frame = ttk.Frame(self)
        frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        list_header = ttk.Label(frame, text="Itens selecionados:", font=("Segoe UI", 10, "bold"))
        list_header.grid(row=0, column=0, sticky="w")

        self._listbox = tk.Listbox(frame, selectmode=tk.EXTENDED, font=("Consolas", 10))
        self._listbox.grid(row=1, column=0, sticky="nsew", pady=4)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for column in range(4):
            buttons_frame.columnconfigure(column, weight=1)

        ttk.Button(buttons_frame, text="Adicionar arquivos", command=self._add_files).grid(
            row=0, column=0, padx=4, pady=2, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Adicionar pasta", command=self._add_folder).grid(
            row=0, column=1, padx=4, pady=2, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Remover seleção", command=self._remove_selected).grid(
            row=0, column=2, padx=4, pady=2, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Limpar lista", command=self._clear_items).grid(
            row=0, column=3, padx=4, pady=2, sticky="ew"
        )

        destination_frame = ttk.LabelFrame(self, text="Destino")
        destination_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        destination_frame.columnconfigure(1, weight=1)

        ttk.Label(destination_frame, text="Arquivo de saída:").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        self._output_var = tk.StringVar()
        self._output_entry = ttk.Entry(destination_frame, textvariable=self._output_var)
        self._output_entry.grid(row=0, column=1, padx=6, pady=4, sticky="ew")
        ttk.Button(destination_frame, text="Procurar", command=self._choose_output).grid(
            row=0, column=2, padx=6, pady=4
        )

        ttk.Label(destination_frame, text="Nível de compactação:").grid(
            row=1, column=0, padx=6, pady=4, sticky="w"
        )
        self._level = tk.IntVar(value=9)
        level_scale = ttk.Scale(
            destination_frame,
            from_=0,
            to=9,
            orient="horizontal",
            command=lambda _: self._level_label.configure(text=str(int(self._level.get()))),
            variable=self._level,
        )
        level_scale.grid(row=1, column=1, padx=6, pady=4, sticky="ew")
        self._level_label = ttk.Label(destination_frame, text="9", width=3)
        self._level_label.grid(row=1, column=2, padx=6, pady=4)

        self._progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self._progress.grid(row=3, column=0, sticky="ew", padx=12, pady=6)

        self._status_var = tk.StringVar(value="Pronto")
        status_label = ttk.Label(self, textvariable=self._status_var, anchor="w")
        status_label.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 6))

        action_frame = ttk.Frame(self)
        action_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=6)
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(2, weight=1)

        self._compress_btn = ttk.Button(action_frame, text="Compactar", command=self._start_compress)
        self._compress_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self._decompress_btn = ttk.Button(action_frame, text="Extrair", command=self._start_decompress)
        self._decompress_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self._cancel_btn = ttk.Button(action_frame, text="Cancelar", command=self._cancel_current, state=tk.DISABLED)
        self._cancel_btn.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        self.drop_target_register(tk.DND_FILES) if hasattr(self, "drop_target_register") else None

    # -- File handling ----------------------------------------------------
    def _add_items(self, items: Iterable[str]) -> None:
        count = 0
        for item in items:
            path = Path(item).expanduser()
            if path.exists() and path not in self._items:
                self._items.append(path)
                self._listbox.insert(tk.END, str(path))
                count += 1
        if count:
            self._status_var.set(f"{count} item(ns) adicionados")

    def _add_files(self) -> None:
        files = filedialog.askopenfilenames(title="Selecionar arquivos")
        if files:
            self._add_items(files)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecionar pasta")
        if folder:
            self._add_items([folder])

    def _remove_selected(self) -> None:
        selection = list(self._listbox.curselection())
        for index in reversed(selection):
            del self._items[index]
            self._listbox.delete(index)

    def _clear_items(self) -> None:
        self._items.clear()
        self._listbox.delete(0, tk.END)

    def _choose_output(self) -> None:
        initial = self._output_var.get() or "arquivo"
        filename = filedialog.asksaveasfilename(
            defaultextension=".pwr",
            filetypes=[("Arquivos PowRAR", "*.pwr"), ("Todos os arquivos", "*.*")],
            initialfile=initial,
            title="Salvar arquivo"
        )
        if filename:
            self._output_var.set(filename)

    # -- Compression / decompression -------------------------------------
    def _ensure_idle(self) -> bool:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Operação em andamento", "Aguarde a conclusão da tarefa atual.")
            return False
        return True

    def _start_worker(self, task: _TaskRequest) -> None:
        if not self._ensure_idle():
            return

        self._progress.configure(value=0, maximum=1)
        self._status_var.set("Processando...")
        self._cancel_event.clear()
        self._compress_btn.configure(state=tk.DISABLED)
        self._decompress_btn.configure(state=tk.DISABLED)
        self._cancel_btn.configure(state=tk.NORMAL)

        def runner() -> None:
            try:
                if task.kind == "compress":
                    def callback(done: int, total: int) -> None:
                        self._queue.put(("progress", (done, total)))

                    settings = CompressionSettings(level=task.level)
                    archive = compress(task.sources, task.destination, settings=settings, progress=callback, cancel_event=self._cancel_event)
                    self._queue.put(("done", archive))
                else:
                    def callback(done: int, total: int) -> None:
                        self._queue.put(("progress", (done, total)))

                    settings = DecompressionSettings()
                    decompress(task.sources[0], task.destination, settings=settings, progress=callback, cancel_event=self._cancel_event)
                    self._queue.put(("done", task.destination))
            except OperationCancelled:
                self._queue.put(("cancelled", None))
            except Exception as exc:  # noqa: BLE001 - display detailed error to the user
                self._queue.put(("error", exc))

        self._worker = threading.Thread(target=runner, daemon=True)
        self._worker.start()

    def _start_compress(self) -> None:
        if not self._items:
            messagebox.showwarning("Nenhum item", "Adicione arquivos ou pastas para compactar.")
            return

        destination = self._output_var.get()
        if not destination:
            first = self._items[0]
            destination = str(default_archive_name(first.with_suffix("")))
            self._output_var.set(destination)

        task = _TaskRequest("compress", list(self._items), Path(destination), int(self._level.get()))
        self._start_worker(task)

    def _start_decompress(self) -> None:
        if not self._ensure_idle():
            return

        archive_path = filedialog.askopenfilename(
            title="Selecionar arquivo PowRAR",
            filetypes=[("Arquivos PowRAR", "*.pwr"), ("Todos os arquivos", "*.*")],
        )
        if not archive_path:
            return

        destination = filedialog.askdirectory(title="Selecionar pasta de destino")
        if not destination:
            return

        task = _TaskRequest("decompress", [Path(archive_path)], Path(destination), int(self._level.get()))
        self._start_worker(task)

    def _cancel_current(self) -> None:
        if self._worker and self._worker.is_alive():
            self._cancel_event.set()
            self._status_var.set("Cancelando...")

    # -- Background coordination -----------------------------------------
    def _poll_queue(self) -> None:
        try:
            while True:
                message, payload = self._queue.get_nowait()
                if message == "progress":
                    done, total = payload  # type: ignore[misc]
                    self._progress.configure(maximum=total, value=done)
                    if total:
                        percent = min(100, int(done / total * 100))
                        self._status_var.set(f"Processando... {percent}%")
                elif message == "done":
                    target = payload
                    self._status_var.set(f"Concluído: {target}")
                    messagebox.showinfo("Sucesso", f"Operação concluída com sucesso!\n{target}")
                    self._finalize_worker()
                elif message == "error":
                    self._status_var.set("Falha na operação")
                    messagebox.showerror("Erro", f"Ocorreu um problema:\n{payload}")
                    self._finalize_worker()
                elif message == "cancelled":
                    self._status_var.set("Operação cancelada")
                    messagebox.showinfo("Cancelado", "A operação foi cancelada pelo usuário.")
                    self._finalize_worker()
        except queue.Empty:
            pass
        finally:
            self.after(150, self._poll_queue)

    def _finalize_worker(self) -> None:
        self._progress.configure(value=0)
        self._cancel_event.clear()
        self._compress_btn.configure(state=tk.NORMAL)
        self._decompress_btn.configure(state=tk.NORMAL)
        self._cancel_btn.configure(state=tk.DISABLED)


def run_app() -> None:
    app = PowRARApp()
    app.mainloop()


__all__ = ["PowRARApp", "run_app"]
