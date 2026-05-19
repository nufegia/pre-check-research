from __future__ import annotations

from pcr_audit.adapter_runtime.base import AuditRunContext


PRODUCT_ADAPTER_ORDER = [
    "reference_audit",
    "citation_claim_check",
    "papermill_light_signals",
    "papermill_network_signals",
    "image_extract",
    "image_duplicate_internal",
    "image_copy_move_internal",
    "image_metadata_audit",
    "western_blot_review_list",
    "provenance_hash",
    "provenance_chain_verify",
    "code_rerun_audit",
    "code_rerun_execute",
]

IMAGE_TOOL_IDS = {
    "image_extract",
    "image_duplicate_internal",
    "image_copy_move_internal",
    "image_metadata_audit",
    "western_blot_review_list",
}


def product_adapter(context: AuditRunContext, tool_id: str) -> None:
    from pcr_audit.data_trace import run_code_sandbox
    from pcr_audit.product import code_audit, corpus_signals, image_audit, provenance, reference_audit

    if tool_id == "reference_audit":
        context.product_results.append(reference_audit.analyze_references(context.source))
    elif tool_id == "citation_claim_check":
        context.product_results.append(reference_audit.analyze_citation_claims(context.source))
    elif tool_id == "papermill_light_signals":
        context.product_results.append(reference_audit.analyze_papermill_signals(context.source))
    elif tool_id == "papermill_network_signals":
        context.product_results.append(corpus_signals.analyze_papermill_network_signals(context.source))
    elif tool_id in IMAGE_TOOL_IDS:
        if not any(result.name in IMAGE_TOOL_IDS for result in context.product_results):
            context.product_results.extend(image_audit.analyze_images(context.source, context.workdir / "images"))
    elif tool_id == "provenance_hash":
        context.product_results.append(provenance.analyze_provenance(context.source))
    elif tool_id == "provenance_chain_verify":
        context.product_results.append(provenance.provenance_payload_to_result(context.source, provenance.provenance_verify(context.source)))
    elif tool_id == "code_rerun_audit":
        context.product_results.append(code_audit.analyze_code_files(context.source))
    elif tool_id == "code_rerun_execute":
        code_result, _derived_outputs = run_code_sandbox(context.source, [context.source], context.workdir, 60, True)
        context.product_results.append(code_result)
