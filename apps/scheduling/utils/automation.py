# automation.py
from apps.scheduling.models import ShiftSwapRequest

from .matchers import SwapMatcher


class SwapOptimizer:
    def suggest_swaps(self):
        open_requests = ShiftSwapRequest.objects.filter(status="open")

        for request in open_requests:
            matches = SwapMatcher(request).find_matches()
            ranked_matches = self._rank_matches(matches, request)
            self._notify_potential_swappers(request, ranked_matches[:3])

    def _rank_matches(self, matches, request):
        return sorted(
            matches,
            key=lambda u: (
                -u.qualifications.count(),  # Prefer more qualified
                u.current_workload(),       # Prefer lighter workload
                u.proximity_to(request.original_shift.location)
            )
        )

    # def _notify_potential_swappers(self, request, matches):
    #     for user in matches:
    #         NotificationService.send_swap_suggestion(
    #             user=user,
    #             swap_request=request
    #         )
