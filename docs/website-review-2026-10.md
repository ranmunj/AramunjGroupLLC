# Website positioning review

## Changes made

- Lead with IT consulting for small businesses and global enterprises, followed by concrete data, software-upgrade, and application-delivery needs.
- Group the offer into nine services with practical deliverables, rather than a long list of overlapping technologies.
- Explain focused small-business work, growth-stage improvements, and enterprise modernization separately.
- Add linked, actual website previews for Zimbabwe Global Talent Network and LumiBright Zimbabwe. Avoid unverified usage statistics or outcome claims.
- Replace generic bank-name highlights with specific founder experience at Credit One Bank, Citi, and Bank of America (via Apex Systems), based on the supplied resume.
- Use the corrected Purpose Financial title, Data Release Manager. Include Snowflake, dbt, and Data Vault context from the user's messages in the Purpose financial chat, without internal project names or colleague details.
- Distinguish individual career experience from Aramunj client relationships or endorsements.
- Explain international collaboration, time-zone planning, regional requirements, and knowledge transfer without inventing offices or geographic delivery statistics.
- Keep the original brand and founder photograph, with the portrait small and to the right of the name.
- Replace the generic LinkedIn URL with the founder's profile. Remove nonfunctional placeholder privacy/terms links rather than presenting nonexistent policies.
- Preserve all contact API field names and database behavior. Add duplicate-submit protection and visitor-friendly failure messages that preserve form entries. Per the latest request, use aramunj@icloud.com for public contact details and as the default inquiry notification recipient, and set the Render INQUIRY_RECIPIENT to this same single address. Leave SMTP sender credentials unchanged.
- Compress the new portfolio previews as WebP, use lazy loading below the fold, and pause the decorative canvas when offscreen or the tab is hidden. Content remains visible without JavaScript.

## Recommended next steps

1. Prepare and approve a real privacy notice covering inquiry data, recipients, retention, and contact rights before adding a policy link. Obtain appropriate review rather than using placeholder legal text.
2. Develop short, permission-cleared case studies for the two portfolio projects: the business need, your contribution, deliverables, and verifiable results.
3. Confirm inbox receipt of a clearly labeled end-to-end submission test after deployment. SMTP acceptance alone does not establish inbox delivery. Inquiry database settings are unchanged.
4. Add service-specific pages as demand becomes clear, starting with software modernization and small-business data management. Avoid many thin pages that repeat the homepage.
5. Review release monitoring, backup/restore testing, and inquiry spam protection as a separate backend task.

## Repeating the checks

```text
node --test tests/site.test.cjs
python -m unittest discover -s tests -p "test_*.py" -v
```

The automated checks cover inquiry payload compatibility, duplicate submissions,
success/failure behavior, navigation closure, anchor targets, image files and
attributes, structured data, required fields, and portfolio/profile links.
They do not send real emails or write production inquiries.
