import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { SearchInput } from '@/components/ui/SearchInput';
import { DataTable, type Column } from '@/components/ui/DataTable';
import {
  Sparkles,
  BookOpen,
  Calendar,
} from 'lucide-react';

interface PolicyDocumentRow {
  id: string;
  familyId: string;
  title: string;
  documentType: string;
  version: string;
  chunkCount: number;
  effectiveFrom: string;
  status: 'ACTIVE' | 'ARCHIVED';
}

const SAMPLE_POLICY_DOCS: PolicyDocumentRow[] = [
  {
    id: 'DOC-ESG-001',
    familyId: 'FAM-ESG-EXCLUSION',
    title: 'ESG Exclusion Policy',
    documentType: 'ESG_EXCLUSION',
    version: '1.0',
    chunkCount: 4,
    effectiveFrom: '2026-01-01',
    status: 'ACTIVE',
  },
  {
    id: 'DOC-IPS-001',
    familyId: 'FAM-GROWTH-MANDATE',
    title: 'Aggressive Growth Investment Policy Statement',
    documentType: 'INVESTMENT_POLICY_STATEMENT',
    version: '2.1',
    chunkCount: 8,
    effectiveFrom: '2025-06-01',
    status: 'ACTIVE',
  },
  {
    id: 'DOC-FEE-001',
    familyId: 'FAM-EXECUTION-SCHEDULE',
    title: 'Tiered Brokerage Fee Schedule',
    documentType: 'FEE_SCHEDULE',
    version: '1.0',
    chunkCount: 3,
    effectiveFrom: '2025-01-01',
    status: 'ACTIVE',
  },
];

export function PoliciesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [askQuery, setAskQuery] = useState('What are the rules regarding thermal coal and tobacco revenue?');
  const [activeTab, setActiveTab] = useState<'library' | 'search' | 'ask'>('ask');

  const columns: Column<PolicyDocumentRow>[] = [
    {
      key: 'title',
      header: 'Document Title & Family ID',
      render: (item) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-slate-100 block">{item.title}</span>
          <span className="font-mono text-[10px] text-slate-400">{item.familyId} &bull; {item.id}</span>
        </div>
      ),
    },
    {
      key: 'documentType',
      header: 'Category',
      render: (item) => (
        <Badge
          variant={item.documentType === 'ESG_EXCLUSION' ? 'success' : item.documentType === 'FEE_SCHEDULE' ? 'warning' : 'brand'}
          size="sm"
        >
          {item.documentType}
        </Badge>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      align: 'center',
      render: (item) => <span className="font-mono text-xs">v{item.version}</span>,
    },
    {
      key: 'chunkCount',
      header: 'Chunks',
      align: 'center',
      render: (item) => <span className="font-mono text-xs">{item.chunkCount} chunks</span>,
    },
    {
      key: 'effectiveFrom',
      header: 'Effective Date',
      render: (item) => <span className="font-mono text-[11px] text-slate-500">{item.effectiveFrom}</span>,
    },
    {
      key: 'status',
      header: 'Temporal Status',
      render: (item) => (
        <Badge variant={item.status === 'ACTIVE' ? 'success' : 'neutral'} size="sm">
          {item.status}
        </Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Compliance Policy RAG &amp; Intelligence
            </h2>
            <Badge variant="brand" size="sm">
              FASTEMBED ONNX
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Grounded semantic policy retrieval, temporal validity filtering, and verified chunk citations.
          </p>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
          <button
            type="button"
            onClick={() => setActiveTab('ask')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'ask'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            Ask Policy (Q&amp;A)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('library')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'library'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            Policy Library
          </button>
        </div>
      </div>

      {/* RAG Architecture Notice */}
      <Alert variant="info" title="Sandboxed Semantic Retrieval Boundary">
        FastEmbed ONNX generates local 384-dimensional dense vectors (<code>BAAI/bge-small-en-v1.5</code>) with cosine similarity ranking. Explanations cite exact document chunk IDs. If the local Ollama daemon is offline, the system safely falls back to deterministic chunk evidence excerpts.
      </Alert>

      {/* Q&A Workbench Tab */}
      {activeTab === 'ask' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Grounded Compliance Question Answering</CardTitle>
              </div>
              <CardDescription>
                Ask a natural language query against active investment mandates and ESG exclusion policies
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="flex-1">
                  <SearchInput
                    value={askQuery}
                    onChange={setAskQuery}
                    placeholder="Ask a compliance or mandate question..."
                  />
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-mono">As-of: 2026-01-15</span>
                  </div>
                  <Button variant="primary" size="md">
                    Retrieve &amp; Answer
                  </Button>
                </div>
              </div>

              {/* Grounded Answer Presentation Box */}
              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="success" size="sm">ANSWERED WITH CITATIONS</Badge>
                    <Badge variant="brand" size="sm">FastEmbed Cosine: 0.8245</Badge>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">Retrieved 1 chunk</span>
                </div>

                <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
                  Zero holdings are permitted in companies deriving revenue from tobacco leaf cultivation or manufacturing. Companies generating greater than 5% of gross annual revenues from thermal coal extraction or coal-fired power generation are barred from investment portfolios designated under the ESG mandate{' '}
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300 font-mono text-[10px] font-semibold cursor-pointer" title="DOC-ESG-001:chunk-002">
                    [DOC-ESG-001:chunk-002]
                  </span>.
                </div>

                {/* Cited Evidence Inspector */}
                <div className="pt-3 border-t border-slate-200 dark:border-slate-700/80">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                    <BookOpen className="w-3.5 h-3.5 text-brand-600" />
                    <span>Verified Policy Chunk Evidence</span>
                  </div>
                  <div className="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 font-mono text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-1 mb-1">
                      <span>DOC-ESG-001 &bull; Section: Exclusion Criteria</span>
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Similarity: 82.5%</span>
                    </div>
                    <p className="italic">
                      "Zero holdings permitted in companies deriving revenue from tobacco leaf cultivation... Companies generating greater than 5% from thermal coal are barred."
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Policy Library Table Tab */}
      {activeTab === 'library' && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle>Policy Document Vector Library</CardTitle>
                <CardDescription>
                  Vectorized compliance documents, version histories, and temporal boundaries
                </CardDescription>
              </div>
              <div className="w-64">
                <SearchInput
                  value={searchQuery}
                  onChange={setSearchQuery}
                  placeholder="Filter documents..."
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={columns}
              data={SAMPLE_POLICY_DOCS.filter((d) =>
                d.title.toLowerCase().includes(searchQuery.toLowerCase())
              )}
              keyExtractor={(item) => item.id}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
