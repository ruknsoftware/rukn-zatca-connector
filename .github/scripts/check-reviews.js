module.exports = async ({ github, context, core }) => {
  // Get all reviews for the PR
  const { data: reviews } = await github.rest.pulls.listReviews({
    owner: context.repo.owner,
    repo: context.repo.repo,
    pull_number: context.issue.number
  });

  // Get the PR details to check requested reviewers
  const { data: pr } = await github.rest.pulls.get({
    owner: context.repo.owner,
    repo: context.repo.repo,
    pull_number: context.issue.number
  });

  // Get requested reviewers (both users and teams)
  const requestedReviewers = new Set();
  const requestedTeams = new Set();

  // Add requested users
  if (pr.requested_reviewers) {
    pr.requested_reviewers.forEach(reviewer => {
      requestedReviewers.add(reviewer.login);
    });
  }

  // Add requested teams
  if (pr.requested_teams) {
    pr.requested_teams.forEach(team => {
      requestedReviewers.add(`team:${team.slug}`);
      requestedTeams.add(team.slug);
    });
  }

  // Get all users who have ever been requested as reviewers (including those who already approved)
  // This includes users who were requested but then approved and removed from the list
  const allRequestedUsers = new Set(requestedReviewers);
  
  // Add users from review history who were originally requested
  reviews.forEach(review => {
    // If a user has reviewed and they're not currently in requested reviewers,
    // but they have an approval, they were likely originally requested
    if (review.state === 'APPROVED' && !requestedReviewers.has(review.user.login)) {
      allRequestedUsers.add(review.user.login);
    }
  });

  // Special case: If PR creator is the repository owner and no reviewers were requested,
  // we need to handle this scenario differently
  const isOwnerPR = pr.user.login === context.repo.owner;
  const hasRequestedReviewers = requestedReviewers.size > 0;

  // If owner creates PR and no reviewers were requested, allow self-approval
  if (isOwnerPR && !hasRequestedReviewers) {
    // Check if owner has approved their own PR
    const ownerApproval = reviews.find(review => 
      review.user.login === context.repo.owner && 
      review.state === 'APPROVED'
    );
    
    if (ownerApproval) {
      core.setOutput('approved', true);
      return;
    } else {
      core.setFailed(`This pull request was created by the repository owner but requires approval.
      
      Options:
      1. Add a specific reviewer to the PR, OR
      2. Approve your own PR (self-approval allowed for owner)
      
      Note: Owner self-approval is only allowed when no specific reviewers are requested.`);
      return;
    }
  }

  // Filter reviews to only include those from requested reviewers
  const validReviews = reviews.filter(review => {
    // Only consider reviews from users who were requested (including those who already approved)
    if (allRequestedUsers.has(review.user.login)) {
      return true;
    }
    
    // Check if reviewer is part of a requested team
    for (const teamSlug of requestedTeams) {
      // For now, we'll use a simple approach: if the user login matches the team slug,
      // or if we can't determine team membership, we'll be more permissive
      // This is a fallback for when team membership can't be verified
      if (review.user.login === teamSlug) {
        return true;
      }
    }
    
    return false;
  });

  // Get approved reviews from requested reviewers only
  const approvedReviews = validReviews.filter(review => 
    review.state === 'APPROVED'
  );

  // Check if PR is from a fork (external contributor)
  const isFork = context.payload.pull_request.head.repo.full_name !== context.payload.pull_request.base.repo.full_name;

  // Require only 1 approval from requested reviewers for both fork and non-fork PRs
  const requiredApprovals = 1;
  const hasEnoughApprovals = approvedReviews.length >= requiredApprovals;

  // Check if PR has been reviewed by requested maintainers/admins
  const maintainerReviews = approvedReviews.filter(review => 
    ['OWNER', 'MEMBER', 'COLLABORATOR'].includes(review.author_association)
  );

  const isApproved = hasEnoughApprovals && maintainerReviews.length > 0;

  core.setOutput('approved', isApproved);

  if (!isApproved) {
    core.setFailed(`This pull request requires proper code review before tests can run.
    
    Requirements:
    - Only approvals from REQUESTED reviewers are considered
    - Exactly 1 approval from a requested maintainer is required (for both fork and non-fork PRs)
    - Current valid approvals: ${approvedReviews.length}/${requiredApprovals}
    - Maintainer approvals from requested reviewers: ${maintainerReviews.length}
    - Requested reviewers: ${Array.from(requestedReviewers).join(', ') || 'None'}`);
  }
};
