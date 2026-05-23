"use client";
import dynamic from "next/dynamic";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center text-gray-400 text-sm">
      Loading editor…
    </div>
  ),
});

interface Props {
  value: string;
  onChange: (val: string) => void;
  highlightLine?: number | null;
}

export function CodeEditor({ value, onChange, highlightLine }: Props) {
  return (
    <div className="h-[60vh] border border-[var(--border)] rounded-lg overflow-hidden">
      <MonacoEditor
        height="100%"
        defaultLanguage="sol"
        language="sol"
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        beforeMount={(monaco) => {
          // Register a minimal Solidity language for syntax coloring
          if (
            !monaco.languages.getLanguages().find((l) => l.id === "sol")
          ) {
            monaco.languages.register({ id: "sol" });
            monaco.languages.setMonarchTokensProvider("sol", {
              keywords: [
                "pragma", "solidity", "contract", "interface", "library",
                "function", "modifier", "event", "struct", "enum", "mapping",
                "public", "private", "internal", "external", "view", "pure",
                "payable", "returns", "return", "if", "else", "for", "while",
                "do", "break", "continue", "require", "assert", "revert",
                "memory", "storage", "calldata", "address", "uint", "int",
                "bool", "string", "bytes", "true", "false", "this", "super",
                "new", "delete", "using", "import", "is", "as", "constant",
                "immutable", "anonymous", "indexed", "override", "virtual",
              ],
              tokenizer: {
                root: [
                  [/\/\/.*$/, "comment"],
                  [/\/\*/, "comment", "@comment"],
                  [/"([^"\\]|\\.)*$/, "string.invalid"],
                  [/"/, "string", "@string"],
                  [/[A-Z][\w$]*/, "type"],
                  [
                    /[a-z_$][\w$]*/,
                    {
                      cases: {
                        "@keywords": "keyword",
                        "@default": "identifier",
                      },
                    },
                  ],
                  [/\d+/, "number"],
                ],
                comment: [
                  [/[^\/*]+/, "comment"],
                  [/\*\//, "comment", "@pop"],
                  [/[\/*]/, "comment"],
                ],
                string: [
                  [/[^\\"]+/, "string"],
                  [/"/, "string", "@pop"],
                ],
              },
            });
          }
        }}
        onMount={(editor) => {
          if (highlightLine) {
            editor.revealLineInCenter(highlightLine);
          }
        }}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          fontFamily: "ui-monospace, Menlo, monospace",
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: "on",
        }}
      />
    </div>
  );
}
