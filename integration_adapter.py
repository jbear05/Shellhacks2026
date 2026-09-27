def select_best_candidate(project, candidates):
    """Select the best candidate for a given project.

    Heuristic: prefer exact/substring name matches (boost score), then highest score.
    """
    best = None
    best_score = float('-inf')

    title = (project.get("title") or "").lower()

    for c in candidates:
        score = c.get("score", 0)
        name = (c.get("name") or "").lower()

        # boost when names clearly match
        if name and title and (name in title or title in name):
            score += 3

        if score > best_score:
            best_score = score
            best = c

    return best


def map_project(project, candidates):
    """Map a single extracted project to the best geolocator candidate.

    Returns a merged dict containing project info plus chosen candidate fields
    and a simple confidence label.
    """
    best = select_best_candidate(project, candidates)

    if not best:
        return {
            "project_id": project.get("project_id"),
            "project_title": project.get("title"),
            "match": None,
            "confidence": "NO_CANDIDATES"
        }

    orig_score = best.get("score", 0)

    if orig_score >= 7:
        confidence = "HIGH"
    elif orig_score >= 4:
        confidence = "MEDIUM - REVIEW"
    else:
        confidence = "LOW - MANUAL REVIEW"

    return {
        "project_id": project.get("project_id"),
        "project_title": project.get("title"),
        "in_service_date": project.get("in_service_date"),
        "match_name": best.get("name"),
        "match_operator": best.get("operator"),
        "match_voltage": best.get("voltage"),
        "latitude": best.get("latitude"),
        "longitude": best.get("longitude"),
        "osm_id": best.get("osm_id"),
        "osm_type": best.get("osm_type"),
        "match_score": best.get("score"),
        "confidence": confidence,
        "reasons": best.get("reasons", []),
    }


__all__ = ["select_best_candidate", "map_project"]
